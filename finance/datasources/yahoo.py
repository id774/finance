#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/datasources/yahoo.py: Yahoo Finance price source
#
#  Description:
#  Fetch daily prices from Yahoo Finance through yfinance and normalize
#  them into the canonical frame the pipeline expects.
#
#  This replaces two dead routes to the same provider. Market indices
#  were read through pandas-datareader's Yahoo reader, withdrawn in
#  2017, and Japanese shares were scraped page by page out of the Yahoo
#  Japan history pages over plain HTTP, which no longer exist. Keeping
#  Yahoo as the provider is deliberate: it is the narrowest possible
#  move, and it leaves the meaning of the numbers as close to the stored
#  history as any available option.
#
#  Normalization is the whole point of this module. Everything the
#  client does differently from the old readers is corrected here so
#  that no difference reaches the analysis code:
#
#  - auto_adjust is switched off, because the modern default drops the
#    Adj Close column that every indicator is computed from. A response
#    without Adj Close is refused rather than back-filled from Close,
#    which would silently substitute unadjusted prices.
#  - The tz-aware index is localized away and normalized to midnight, so
#    that a date cannot shift by a day against the stored CSV.
#  - Dividends, stock splits and capital gains are dropped, and the
#    remaining six columns are put in canonical order.
#  - The frame is reindexed to business days, which is what the old
#    Japanese reader returned and what the indicator layer expects.
#
#  One difference cannot be normalized away and is documented rather
#  than hidden: Yahoo's Adj Close is adjusted for splits and dividends,
#  while the Yahoo Japan figure the old scraper read was adjusted for
#  splits only. Indicators of a dividend-paying Japanese share computed
#  from newly fetched rows therefore rest on a slightly different basis
#  than ones computed years ago. Stored history is never rewritten, so
#  this applies to new rows only, and market indices are unaffected. See
#  doc/DATA_CONTRACT.md.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, yfinance
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from finance.datasources import CANONICAL_COLUMNS
from finance.errors import DataSourceError
from finance.stocklist import INDEX_CODES

# Columns yfinance adds that the canonical frame does not carry.
DROPPED_COLUMNS = ("Dividends", "Stock Splits", "Capital Gains")

TOKYO_SUFFIX = ".T"

logger = logging.getLogger(__name__)


def to_symbol(code: str) -> str:
    """
    Translate a stock list code into a Yahoo Finance symbol.

    Market indices carry a caret, matching the symbols the old reader
    was given; anything else is a Tokyo listing.
    """
    if code in INDEX_CODES:
        return "^{0}".format(code)
    return "{0}{1}".format(code, TOKYO_SUFFIX)


def normalize(frame: pd.DataFrame, code: str) -> pd.DataFrame:
    """
    Reshape a yfinance response into the canonical frame.

    Args:
        frame: The frame as returned by yfinance.
        code: The stock code, used only in error messages.

    Returns:
        A frame carrying exactly CANONICAL_COLUMNS on a tz-naive
        business day index.

    Raises:
        DataSourceError: A required column is absent from the response.
    """
    if frame is None or frame.empty:
        return pd.DataFrame(columns=list(CANONICAL_COLUMNS))

    frame = frame.copy()

    # A multi-symbol request returns a column MultiIndex. One symbol is
    # requested at a time, so the outer level carries no information.
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)

    frame = frame.drop(columns=[c for c in DROPPED_COLUMNS if c in frame.columns])

    missing = [column for column in CANONICAL_COLUMNS if column not in frame.columns]
    if missing:
        raise DataSourceError(
            "Response for {0} is missing {1}. Prices were requested unadjusted, so "
            "Adj Close must be present.".format(code, ", ".join(missing))
        )

    index = pd.DatetimeIndex(frame.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    frame.index = index.normalize()
    frame = frame[list(CANONICAL_COLUMNS)].sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    return frame.asfreq("B")


class YahooFinanceSource:
    """ Daily prices from Yahoo Finance, normalized to the canonical frame. """

    def __init__(self, client: object | None = None) -> None:
        """
        Args:
            client: An object exposing Ticker(symbol), used to inject a
                double in tests. When omitted, yfinance is imported on
                first use so that the package imports without it.
        """
        self._client = client

    def _resolve_client(self) -> object:
        """
        Return the price client, importing yfinance on first use.

        Raises:
            DataSourceError: yfinance is not installed.
        """
        if self._client is None:
            try:
                import yfinance
            except ImportError as exc:
                raise DataSourceError(
                    "yfinance is not installed. Install it with: pip install yfinance"
                ) from exc
            self._client = yfinance
        return self._client

    def fetch(self, code: str, start: date, end: date) -> pd.DataFrame:
        """
        Return the daily prices of one stock, normalized.

        The end date is advanced by one day because the client treats it
        as exclusive, while every caller in this repository means it
        inclusively.

        Raises:
            DataSourceError: The source could not be reached or answered
                with something unusable.
        """
        symbol = to_symbol(code)
        client = self._resolve_client()
        logger.debug("Fetching %s as %s from %s to %s", code, symbol, start, end)
        try:
            ticker = client.Ticker(symbol)
            raw = ticker.history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                interval="1d",
                auto_adjust=False,
                actions=False,
                raise_errors=True,
            )
        except DataSourceError:
            raise
        except Exception as exc:  # noqa: BLE001 - the client raises its own unrelated types
            raise DataSourceError(
                "Prices for {0} could not be fetched: {1}".format(code, exc)
            ) from exc

        frame = normalize(raw, code)
        logger.info("Fetched %d rows for %s", len(frame.dropna(how="all")), code)
        return frame
