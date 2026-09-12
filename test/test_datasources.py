#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_datasources.py: The price source adapter
#
#  Description:
#  Assert that the J-Quants adapter turns an API response into the
#  canonical frame, and that every difference between what the API
#  returns and what the pipeline expects is corrected inside the
#  adapter.
#
#  No test here opens a socket. The HTTP session is a double answering
#  with payloads shaped like real responses, and every payload in this
#  file is invented: no figure here was fetched from the API, and none
#  may be. The awkward shapes are covered as well -- a paginated answer,
#  a null field, a body that is not JSON, a rejected key, a rate limit,
#  a timeout, and a response carrying only the unadjusted prices.
#
#  Test Cases:
#  - A four character listing code becomes the five character API code.
#  - A five character code is passed through, and a bad one is refused.
#  - The canonical six columns survive in canonical order.
#  - Every column is taken from the adjusted series.
#  - A response without the adjusted fields is refused, not filled from
#    the unadjusted ones.
#  - A required field missing from a later response row is refused.
#  - Dates are parsed, sorted, deduplicated and reindexed to business
#    days, and carry no timezone.
#  - A null figure becomes a gap rather than a zero.
#  - Pagination is followed to the end and the pages are concatenated.
#  - A repeated pagination key is refused rather than looped on.
#  - The API key travels in the x-api-key header and in nothing else.
#  - A missing API key fails before a request is made.
#  - A non-object item in data is refused rather than silently discarded.
#  - 401 and 403 raise AuthenticationError.
#  - 429 raises RateLimitError once the retries are spent.
#  - 400 and 404 raise DataUnavailableError.
#  - A retryable status is retried and then succeeds.
#  - A transport failure and a non-JSON body raise DataSourceError.
#  - An end before the start is answered without a request.
#  - An empty response is a normal answer, not an error.
#  - An unknown source name is refused.
#  - No error message and no log record carries the API key.
#  - An API key echoed back by the provider is redacted rather than
#    suppressing the rest of the message.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, pytest
#
#  Version History:
#  v1.1 2026-09-09
#       Cover rejection of non-object rows in the response data list.
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import logging
from datetime import date

import pytest

from finance.config import JQuantsSettings
from finance.datasources import CANONICAL_COLUMNS, create_source
from finance.datasources.jquants import (
    API_KEY_HEADER,
    JQuantsSource,
    normalize,
    to_api_code,
    to_local_code,
)
from finance.errors import (
    AuthenticationError,
    ConfigurationError,
    DataSourceError,
    DataUnavailableError,
    InvalidStockCodeError,
    RateLimitError,
)

START = date(2024, 1, 4)
END = date(2024, 1, 9)

API_KEY = "test-key-not-a-real-credential"

DATES = ("2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09")


def settings(**overrides) -> JQuantsSettings:
    """ Build settings that never wait between requests. """
    values = {
        "api_key": API_KEY,
        "base_url": "https://api.example.test/v2",
        "timeout": 5.0,
        "max_retries": 3,
        "request_interval": 0.0,
    }
    values.update(overrides)
    return JQuantsSettings(**values)


def row(day: str, base: float, **overrides) -> dict:
    """
    Build one invented daily bar row in the v2 field spelling.

    The unadjusted figures are deliberately offset from the adjusted
    ones, so that a test can tell which series the adapter read.
    """
    record = {
        "Date": day,
        "Code": "72030",
        "O": base + 1000,
        "H": base + 1010,
        "L": base + 990,
        "C": base + 1005,
        "UL": "0",
        "LL": "0",
        "Vo": 90000,
        "Va": 123456789,
        "AdjFactor": 1.0,
        "AdjO": base,
        "AdjH": base + 10,
        "AdjL": base - 10,
        "AdjC": base + 5,
        "AdjVo": 100000,
    }
    record.update(overrides)
    return record


def rows(days=DATES) -> list[dict]:
    """ Build a page of invented rows. """
    return [row(day, 100.0 + index) for index, day in enumerate(days)]


class FakeResponse:
    """ A requests.Response double. """

    def __init__(self, status_code=200, body=None, headers=None, decodable=True):
        self.status_code = status_code
        self._body = body if body is not None else {"data": []}
        self.headers = headers or {}
        self._decodable = decodable

    def json(self):
        if not self._decodable:
            raise ValueError("not json")
        return self._body


class FakeSession:
    """ A requests.Session double recording every call it is given. """

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [FakeResponse(body={"data": rows()})])
        self.error = error
        self.calls: list[dict] = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "params": dict(params or {}), "headers": dict(headers or {}),
             "timeout": timeout}
        )
        if self.error is not None:
            raise self.error
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)


def source(session: FakeSession, **overrides) -> JQuantsSource:
    """ Build a source bound to a session double. """
    return JQuantsSource(settings(**overrides), session=session)


@pytest.mark.parametrize(
    ("code", "expected"),
    [("7203", "72030"), ("6758", "67580"), ("193A", "193A0"), ("72030", "72030")],
)
def test_a_listing_code_becomes_the_api_code(code, expected):
    assert to_api_code(code) == expected


@pytest.mark.parametrize("code", ["", "72", "720301", "72-03", "N225", "GSPC"])
def test_an_impossible_code_is_refused(code):
    with pytest.raises(InvalidStockCodeError):
        to_api_code(code)


def test_the_api_code_maps_back_to_the_listed_form():
    assert to_local_code("72030") == "7203"
    assert to_local_code("193A0") == "193A"


def test_canonical_columns_in_canonical_order():
    frame = normalize(rows(), "7203")
    assert list(frame.columns) == list(CANONICAL_COLUMNS)


def test_every_column_comes_from_the_adjusted_series():
    frame = normalize([row("2024-01-04", 100.0)], "7203")
    assert frame.loc["2024-01-04", "Open"] == 100.0
    assert frame.loc["2024-01-04", "High"] == 110.0
    assert frame.loc["2024-01-04", "Low"] == 90.0
    assert frame.loc["2024-01-04", "Close"] == 105.0
    assert frame.loc["2024-01-04", "Adj Close"] == 105.0
    assert frame.loc["2024-01-04", "Volume"] == 100000.0


def test_a_response_without_the_adjusted_fields_is_refused():
    bare = {key: value for key, value in row("2024-01-04", 100.0).items()
            if not key.startswith("Adj")}
    with pytest.raises(DataSourceError, match="AdjC"):
        normalize([bare], "7203")


def test_a_required_field_missing_from_a_later_row_is_refused():
    response_rows = rows()
    del response_rows[1]["AdjC"]

    with pytest.raises(DataSourceError, match=r"row 2.*AdjC"):
        normalize(response_rows, "7203")


def test_the_index_is_sorted_naive_and_on_business_days():
    frame = normalize(list(reversed(rows())), "7203")

    assert frame.index.tz is None
    assert frame.index.is_monotonic_increasing
    assert (frame.index.hour == 0).all()
    # 4 to 9 January 2024 is four trading days across a weekend, which
    # is reindexed in as the empty rows the pipeline drops.
    assert list(frame.index.strftime("%Y-%m-%d")) == list(DATES)


def test_a_gap_is_reindexed_as_a_business_day():
    frame = normalize([row("2024-01-04", 100.0), row("2024-01-09", 103.0)], "7203")
    assert len(frame) == 4
    assert frame.loc["2024-01-05"].isna().all()


def test_duplicate_dates_keep_the_last_row():
    frame = normalize([row("2024-01-04", 100.0), row("2024-01-04", 200.0)], "7203")
    assert frame.loc["2024-01-04", "Open"] == 200.0


def test_a_null_figure_becomes_a_gap_rather_than_a_zero():
    frame = normalize([row("2024-01-04", 100.0, AdjVo=None)], "7203")
    assert frame["Volume"].isna().all()


def test_an_unreadable_date_is_refused():
    with pytest.raises(DataSourceError, match="date"):
        normalize([row("not-a-date", 100.0)], "7203")


def test_a_non_numeric_field_is_refused():
    with pytest.raises(DataSourceError, match="AdjO"):
        normalize([row("2024-01-04", 100.0, AdjO="high")], "7203")


def test_an_empty_response_is_a_normal_answer():
    frame = normalize([], "7203")
    assert frame.empty
    assert list(frame.columns) == list(CANONICAL_COLUMNS)


def test_fetch_asks_the_expected_endpoint_with_the_expected_parameters():
    session = FakeSession([FakeResponse(body={"data": rows()})])
    source(session).fetch("7203", START, END)

    call = session.calls[0]
    assert call["url"] == "https://api.example.test/v2/equities/bars/daily"
    assert call["params"] == {"code": "72030", "from": "2024-01-04", "to": "2024-01-09"}
    assert call["timeout"] == 5.0


def test_the_api_key_travels_in_the_header_and_nowhere_else():
    session = FakeSession([FakeResponse(body={"data": rows()})])
    source(session).fetch("7203", START, END)

    call = session.calls[0]
    assert call["headers"][API_KEY_HEADER] == API_KEY
    assert API_KEY not in call["url"]
    assert API_KEY not in str(call["params"])


def test_a_missing_api_key_fails_before_any_request():
    session = FakeSession()
    with pytest.raises(AuthenticationError, match="JQUANTS_API_KEY"):
        JQuantsSource(settings(api_key=""), session=session)
    assert session.calls == []


def test_pagination_is_followed_and_the_pages_are_concatenated():
    session = FakeSession(
        [
            FakeResponse(body={"data": rows(DATES[:2]), "pagination_key": "page-2"}),
            FakeResponse(body={"data": rows(DATES[2:])}),
        ]
    )
    frame = source(session).fetch("7203", START, END)

    assert len(session.calls) == 2
    assert session.calls[1]["params"]["pagination_key"] == "page-2"
    assert len(frame.dropna(how="all")) == 4


def test_a_repeated_pagination_key_is_refused():
    session = FakeSession(
        [
            FakeResponse(body={"data": rows(DATES[:2]), "pagination_key": "same"}),
            FakeResponse(body={"data": rows(DATES[2:]), "pagination_key": "same"}),
        ]
    )
    with pytest.raises(DataSourceError, match="pagination"):
        source(session).fetch("7203", START, END)


def test_a_response_without_a_data_member_is_refused():
    session = FakeSession([FakeResponse(body={"rows": []})])
    with pytest.raises(DataSourceError, match="data"):
        source(session).fetch("7203", START, END)


def test_a_non_object_data_row_is_refused():
    session = FakeSession([FakeResponse(body={"data": [row("2024-01-04", 100.0), "not-a-row"]})])
    with pytest.raises(DataSourceError, match=r"page 1.*position 2"):
        source(session).fetch("7203", START, END)
    assert len(session.calls) == 1


@pytest.mark.parametrize("status", [401, 403])
def test_a_rejected_credential_is_an_authentication_error(status):
    session = FakeSession([FakeResponse(status_code=status, body={"message": "denied"})])
    with pytest.raises(AuthenticationError, match=str(status)):
        source(session).fetch("7203", START, END)


def test_a_spent_rate_limit_is_a_rate_limit_error():
    session = FakeSession([FakeResponse(status_code=429, body={"message": "slow down"})])
    with pytest.raises(RateLimitError):
        source(session, max_retries=1).fetch("7203", START, END)


@pytest.mark.parametrize("status", [400, 404])
def test_a_range_outside_the_plan_is_reported_as_unavailable(status):
    session = FakeSession([FakeResponse(status_code=status, body={"message": "out of range"})])
    with pytest.raises(DataUnavailableError):
        source(session).fetch("7203", START, END)


def test_a_retryable_status_is_retried_and_then_succeeds():
    session = FakeSession(
        [FakeResponse(status_code=503), FakeResponse(body={"data": rows()})]
    )
    frame = source(session).fetch("7203", START, END)

    assert len(session.calls) == 2
    assert len(frame.dropna(how="all")) == 4


def test_a_server_error_is_a_data_source_error():
    session = FakeSession([FakeResponse(status_code=500, body={"message": "boom"})])
    with pytest.raises(DataSourceError):
        source(session, max_retries=1).fetch("7203", START, END)


def test_a_transport_failure_is_a_data_source_error():
    session = FakeSession(error=OSError("connection reset"))
    with pytest.raises(DataSourceError, match="could not be reached"):
        source(session, max_retries=2).fetch("7203", START, END)
    assert len(session.calls) == 2


def test_a_body_that_is_not_json_is_a_data_source_error():
    session = FakeSession([FakeResponse(decodable=False)])
    with pytest.raises(DataSourceError, match="not JSON"):
        source(session).fetch("7203", START, END)


def test_an_end_before_the_start_is_answered_without_a_request():
    session = FakeSession()
    frame = source(session).fetch("7203", END, START)

    assert session.calls == []
    assert frame.empty
    assert list(frame.columns) == list(CANONICAL_COLUMNS)


def test_an_invalid_code_fails_before_a_request():
    session = FakeSession()
    with pytest.raises(InvalidStockCodeError):
        source(session).fetch("N225", START, END)
    assert session.calls == []


def test_no_error_message_carries_the_api_key():
    session = FakeSession(
        [FakeResponse(status_code=401, body={"message": "denied {0}".format(API_KEY)})]
    )
    with pytest.raises(AuthenticationError) as caught:
        source(session).fetch("7203", START, END)

    message = str(caught.value)
    assert API_KEY not in message
    assert "[REDACTED]" in message
    assert "denied" in message


def test_no_log_record_carries_the_api_key(caplog):
    session = FakeSession([FakeResponse(status_code=503), FakeResponse(body={"data": rows()})])
    with caplog.at_level(logging.DEBUG):
        source(session).fetch("7203", START, END)
    assert API_KEY not in caplog.text


def test_the_settings_repr_does_not_carry_the_api_key():
    assert API_KEY not in repr(settings())


def test_create_source_builds_the_jquants_source():
    built = create_source(settings())
    assert isinstance(built, JQuantsSource)


def test_create_source_refuses_a_run_without_a_key():
    with pytest.raises(AuthenticationError):
        create_source(settings(api_key=""))


def test_unknown_source_is_refused():
    with pytest.raises(ConfigurationError, match="Unknown data source"):
        create_source(settings(), "quandl")
