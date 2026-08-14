#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/datasources/jquants.py: J-Quants API price source
#
#  Description:
#  Fetch daily Japanese equity prices from the J-Quants API, the data
#  distribution service JPX Market Innovation & Research operates for
#  individual investors, and normalize them into the canonical frame the
#  rest of the pipeline works on.
#
#  Everything peculiar to the provider is here and leaves no trace above
#  it: the API key header, the base URL, the endpoint, its query
#  parameters, pagination, the request interval, retries, timeouts, the
#  HTTP and API error vocabulary, the five digit code form and the
#  abbreviated field names of the v2 response. The analysis layer above
#  receives a frame with the same six columns it has always received and
#  cannot tell which provider filled it.
#
#  Protocol, as published for v2:
#
#  - Base URL https://api.jquants.com/v2, the key sent as the x-api-key
#    request header. The v1 refresh-token exchange, /token/auth_user
#    followed by /token/auth_refresh, was withdrawn on 1 June 2026 and
#    is not implemented.
#  - GET /equities/bars/daily with code, from and to. The response is a
#    JSON object whose "data" member is the list of rows, and whose
#    "pagination_key" member, when present, must be echoed as a query
#    parameter to obtain the next page.
#  - Rows carry abbreviated names. O, H, L, C, Vo and Va are the day's
#    prices, volume and turnover as traded; AdjO, AdjH, AdjL, AdjC and
#    AdjVo are the same figures restated onto the current share basis
#    using AdjFactor.
#
#  Which series is taken, and why:
#
#  The adjusted five are taken for all six canonical columns, with
#  Adj Close and Close both from AdjC. J-Quants adjusts for share
#  splits and reverse splits and not for dividends, which is the basis
#  the stored history was written on when these prices came from the
#  Yahoo Japan history pages. Taking the adjusted series for the whole
#  row also removes an inconsistency that was there before: candles were
#  drawn from unadjusted prices while every indicator was computed from
#  an adjusted close, so a split put a step in the chart that the
#  indicators under it did not have. No formula changed; the series they
#  are computed from is now one basis rather than two. See
#  doc/DATA_CONTRACT.md.
#
#  A row whose adjusted fields are absent is refused rather than filled
#  from the unadjusted ones, because substituting a different basis
#  silently is the failure this module exists to prevent.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, requests
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release, replacing the Yahoo Finance adapter.
#
########################################################################

from __future__ import annotations

import logging
import re
import time
from datetime import date
from typing import Any

import pandas as pd

from finance.config import JQuantsSettings
from finance.datasources import CANONICAL_COLUMNS
from finance.errors import (
    AuthenticationError,
    DataSourceError,
    DataUnavailableError,
    InvalidStockCodeError,
    RateLimitError,
)

DAILY_BARS_PATH = "/equities/bars/daily"

API_KEY_HEADER = "x-api-key"
DATA_KEY = "data"
PAGINATION_KEY = "pagination_key"

# The canonical column each abbreviated response field fills. Only the
# adjusted series is read; see the module description for why.
FIELD_MAP: dict[str, str] = {
    "Open": "AdjO",
    "High": "AdjH",
    "Low": "AdjL",
    "Close": "AdjC",
    "Volume": "AdjVo",
    "Adj Close": "AdjC",
}

DATE_FIELD = "Date"
CODE_FIELD = "Code"

# A listing is named by four characters at the exchange and by five in
# this API, the fifth being a trailing zero. Codes issued since 2024 may
# carry a letter in a later position, as in 193A, so this is not a
# digits-only pattern; the first character is still always a digit,
# which is what tells a listing code from a market index name.
LOCAL_CODE_PATTERN = re.compile(r"^[0-9][0-9A-Z]{3}$")
API_CODE_PATTERN = re.compile(r"^[0-9][0-9A-Z]{4}$")

# A stop against a server that keeps handing back a pagination key. The
# window one call covers is at most a few years of daily rows for one
# listing, so this is far above any legitimate answer.
MAX_PAGES = 200

# Statuses that are worth sending again rather than reporting.
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

logger = logging.getLogger(__name__)


def to_api_code(code: str) -> str:
    """
    Translate a stock list code into the form the API expects.

    Args:
        code: The code as it appears in the stock list, of four
            characters, or already in the five character API form.

    Returns:
        The five character code.

    Raises:
        InvalidStockCodeError: The code cannot name a listing.
    """
    candidate = str(code).strip().upper()
    if LOCAL_CODE_PATTERN.match(candidate):
        return candidate + "0"
    if API_CODE_PATTERN.match(candidate):
        return candidate
    raise InvalidStockCodeError(
        "{0!r} is not a Japanese listing code. Four characters, or five as the API "
        "spells them, are expected.".format(code)
    )


def to_local_code(code: str) -> str:
    """ Translate a five character API code back into the listed form. """
    candidate = str(code).strip().upper()
    if API_CODE_PATTERN.match(candidate) and candidate.endswith("0"):
        return candidate[:4]
    return candidate


def _as_yyyymmdd(value: date) -> str:
    """ Render a date the way the query parameters take it. """
    return value.strftime("%Y-%m-%d")


def _row_value(row: dict[str, Any], field: str) -> float:
    """
    Return one numeric field of a response row.

    A field that is present and null is a day the figure does not exist
    for, which is normal and becomes a gap. A field that is absent
    altogether means the response is not the one this adapter was
    written against, and is refused by the caller.
    """
    value = row[field]
    if value is None or value == "":
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise DataSourceError(
            "Field {0} of the response is not a number: {1!r}".format(field, value)
        ) from exc


def normalize(rows: list[dict[str, Any]], code: str) -> pd.DataFrame:
    """
    Reshape J-Quants daily bar rows into the canonical frame.

    Args:
        rows: The concatenated "data" members of the responses.
        code: The stock code, used in error messages only.

    Returns:
        A frame carrying exactly CANONICAL_COLUMNS on a tz-naive
        business day index. An empty frame when there were no rows,
        which is a normal answer.

    Raises:
        DataSourceError: A row is missing a field this adapter reads.
    """
    if not rows:
        return pd.DataFrame(columns=list(CANONICAL_COLUMNS))

    required = {DATE_FIELD, *FIELD_MAP.values()}
    missing = sorted(required.difference(rows[0]))
    if missing:
        raise DataSourceError(
            "Response for {0} is missing {1}. Adjusted prices are required and are "
            "not substituted from the unadjusted fields.".format(code, ", ".join(missing))
        )

    index = pd.to_datetime([row[DATE_FIELD] for row in rows], errors="coerce")
    if index.hasnans:
        raise DataSourceError("Response for {0} carries an unreadable date".format(code))

    frame = pd.DataFrame(
        {
            column: [_row_value(row, field) for row in rows]
            for column, field in FIELD_MAP.items()
        },
        index=pd.DatetimeIndex(index),
    )
    if frame.index.tz is not None:
        frame.index = frame.index.tz_localize(None)
    frame.index = frame.index.normalize()

    frame = frame[list(CANONICAL_COLUMNS)].sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    return frame.asfreq("B")


class JQuantsSource:
    """
    Daily prices from the J-Quants API, normalized to the canonical frame.

    One instance holds one HTTP session and the clock the request
    interval is measured on, so a run over a stock list reuses the
    connection and paces itself across every stock rather than per
    stock.
    """

    def __init__(self, settings: JQuantsSettings, session: object | None = None) -> None:
        """
        Args:
            settings: Endpoint, credential and pacing.
            session: An object exposing get(url, params, headers,
                timeout), used to inject a double in tests. When
                omitted, requests is imported on first use so that the
                package imports without it.

        Raises:
            AuthenticationError: No API key is configured. This is
                raised here, before a socket is opened, so that a run
                started without the credential fails at once instead of
                once per stock.
        """
        if not settings.has_api_key():
            raise AuthenticationError(
                "No J-Quants API key is configured. Export JQUANTS_API_KEY with the key "
                "issued from the J-Quants dashboard."
            )
        self.settings = settings
        self._session = session
        self._last_request: float | None = None

    def _resolve_session(self) -> object:
        """
        Return the HTTP session, importing requests on first use.

        Raises:
            DataSourceError: requests is not installed.
        """
        if self._session is None:
            try:
                import requests
            except ImportError as exc:
                raise DataSourceError(
                    "requests is not installed. Install it with: pip install requests"
                ) from exc
            self._session = requests.Session()
        return self._session

    def _wait_turn(self) -> None:
        """ Hold the configured minimum interval between two requests. """
        interval = self.settings.request_interval
        if interval <= 0 or self._last_request is None:
            self._last_request = time.monotonic()
            return
        remaining = interval - (time.monotonic() - self._last_request)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request = time.monotonic()

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        """
        Perform one GET and return the decoded body.

        Raises:
            AuthenticationError: The key was rejected.
            RateLimitError: The request was throttled and the retries
                are spent.
            DataUnavailableError: The endpoint or the range is outside
                the subscribed plan.
            DataSourceError: Anything else, including a timeout and a
                body that is not JSON.
        """
        session = self._resolve_session()
        url = self.settings.base_url + path
        headers = {API_KEY_HEADER: self.settings.api_key, "Accept": "application/json"}

        last_error: Exception | None = None
        for attempt in range(1, self.settings.max_retries + 1):
            self._wait_turn()
            try:
                response = session.get(
                    url, params=params, headers=headers, timeout=self.settings.timeout
                )
            except Exception as exc:  # noqa: BLE001 - the client raises its own types
                # A transport failure is retried; the loop reports the
                # last one if none of the attempts get through.
                last_error = exc
                logger.warning(
                    "Request to %s failed on attempt %d of %d",
                    path,
                    attempt,
                    self.settings.max_retries,
                )
                continue

            status = int(getattr(response, "status_code", 0))
            if status == 200:
                return self._decode(response)
            if status in RETRYABLE_STATUSES and attempt < self.settings.max_retries:
                self._pause_after(response, status, attempt)
                continue
            self._raise_for_status(response, status)

        raise DataSourceError(
            "The J-Quants API could not be reached after {0} attempts: {1}".format(
                self.settings.max_retries, last_error
            )
        ) from last_error

    def _pause_after(self, response: object, status: int, attempt: int) -> None:
        """ Wait before resending a request the server refused for now. """
        delay = float(attempt) * max(self.settings.request_interval, 1.0)
        retry_after = self._retry_after(response)
        if retry_after is not None:
            delay = max(delay, retry_after)
        logger.warning(
            "The API answered %d; retrying in %.1fs (attempt %d of %d)",
            status,
            delay,
            attempt,
            self.settings.max_retries,
        )
        time.sleep(delay)

    @staticmethod
    def _retry_after(response: object) -> float | None:
        """ Return the Retry-After header in seconds, when it is usable. """
        headers = getattr(response, "headers", None) or {}
        try:
            value = headers.get("Retry-After")
        except AttributeError:
            return None
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _message(response: object) -> str:
        """
        Return the message the API reported, and nothing else.

        Only the message member is taken. The body is never logged or
        re-raised whole: it carries market data, and an error path is no
        place to copy that into a log file.
        """
        try:
            body = response.json()
        except Exception:  # noqa: BLE001 - any decode failure means no message
            return ""
        if not isinstance(body, dict):
            return ""
        message = body.get("message") or ""
        return str(message)[:200]

    def _decode(self, response: object) -> dict[str, Any]:
        """
        Return the decoded body of a successful response.

        Raises:
            DataSourceError: The body is not a JSON object.
        """
        try:
            body = response.json()
        except Exception as exc:  # noqa: BLE001 - any decode failure is the same fault
            raise DataSourceError(
                "The API answered with a body that is not JSON"
            ) from exc
        if not isinstance(body, dict):
            raise DataSourceError("The API answered with a body that is not an object")
        return body

    def _raise_for_status(self, response: object, status: int) -> None:
        """ Turn a refused response into the error that describes it. """
        detail = self._message(response)
        suffix = ": {0}".format(detail) if detail else ""
        if status in (401, 403):
            raise AuthenticationError(
                "The J-Quants API rejected the credential (HTTP {0}){1}".format(status, suffix)
            )
        if status == 429:
            raise RateLimitError(
                "The J-Quants API rate limit was reached (HTTP 429){0}".format(suffix)
            )
        if status in (400, 404):
            raise DataUnavailableError(
                "The J-Quants API has nothing for this request (HTTP {0}){1}".format(
                    status, suffix
                )
            )
        raise DataSourceError("The J-Quants API answered HTTP {0}{1}".format(status, suffix))

    def _fetch_rows(self, code: str, start: date, end: date) -> list[dict[str, Any]]:
        """ Return every row of the range, following pagination to the end. """
        params = {
            "code": to_api_code(code),
            "from": _as_yyyymmdd(start),
            "to": _as_yyyymmdd(end),
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        for page in range(1, MAX_PAGES + 1):
            body = self._get(DAILY_BARS_PATH, params)
            batch = body.get(DATA_KEY)
            if batch is None:
                raise DataSourceError(
                    "The response for {0} carries no {1} member".format(code, DATA_KEY)
                )
            if not isinstance(batch, list):
                raise DataSourceError(
                    "The {0} member of the response for {1} is not a list".format(DATA_KEY, code)
                )
            rows.extend(item for item in batch if isinstance(item, dict))

            key = body.get(PAGINATION_KEY)
            if not key:
                logger.debug("Read %d rows for %s over %d page(s)", len(rows), code, page)
                return rows
            key = str(key)
            if key in seen:
                raise DataSourceError(
                    "The API repeated a pagination key for {0}".format(code)
                )
            seen.add(key)
            params = {**params, PAGINATION_KEY: key}

        raise DataSourceError(
            "The API paginated past {0} pages for {1}".format(MAX_PAGES, code)
        )

    def fetch(self, code: str, start: date, end: date) -> pd.DataFrame:
        """
        Return the daily prices of one stock, normalized.

        An end before the start is answered with an empty frame rather
        than a request: it is what the caller means when the stored
        history already reaches the newest date the plan publishes.

        Raises:
            DataSourceError: The source could not be reached or answered
                with something unusable. AuthenticationError,
                RateLimitError, DataUnavailableError and
                InvalidStockCodeError are the subtypes a caller may want
                to tell apart.
        """
        if end < start:
            logger.debug("Nothing to request for %s: %s is after %s", code, start, end)
            return pd.DataFrame(columns=list(CANONICAL_COLUMNS))

        logger.debug("Fetching %s from %s to %s", code, start, end)
        rows = self._fetch_rows(code, start, end)
        frame = normalize(rows, code)
        logger.info("Fetched %d rows for %s", len(frame.dropna(how="all")), code)
        return frame
