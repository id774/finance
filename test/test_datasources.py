#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_datasources.py: The price source adapter
#
#  Description:
#  Assert that the Yahoo adapter turns a client response into the
#  canonical frame, and that every difference between what the client
#  returns and what the pipeline expects is corrected inside the
#  adapter.
#
#  No test here opens a socket. The client is a double returning frames
#  shaped like real responses, including the awkward shapes: a tz-aware
#  index, a column MultiIndex, the action columns, and a response that
#  has no Adj Close because the caller forgot to disable auto
#  adjustment. Networked checks live in test/integration/.
#
#  Test Cases:
#  - Index codes map to caret symbols and everything else to .T.
#  - The canonical six columns survive in canonical order.
#  - Dividends, stock splits and capital gains are dropped.
#  - A tz-aware index is localized away and normalized to midnight.
#  - A column MultiIndex is flattened.
#  - The frame is sorted and reindexed to business days.
#  - Duplicate dates keep the last row.
#  - A response without Adj Close is refused, not filled from Close.
#  - An empty response is a normal answer, not an error.
#  - A client exception becomes DataSourceError.
#  - Prices are requested with auto_adjust switched off.
#  - The end date is passed inclusively.
#  - An unknown source name is refused.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, pytest
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from finance.datasources import CANONICAL_COLUMNS, create_source
from finance.datasources.yahoo import YahooFinanceSource, normalize, to_symbol
from finance.errors import ConfigurationError, DataSourceError

START = date(2024, 1, 4)
END = date(2024, 1, 9)


def response(index=None, **overrides) -> pd.DataFrame:
    """ Build a frame shaped like a yfinance response. """
    index = index if index is not None else pd.to_datetime(
        ["2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09"]
    )
    data = {
        "Open": [100.0, 101.0, 102.0, 103.0],
        "High": [110.0, 111.0, 112.0, 113.0],
        "Low": [90.0, 91.0, 92.0, 93.0],
        "Close": [105.0, 106.0, 107.0, 108.0],
        "Adj Close": [104.0, 105.0, 106.0, 107.0],
        "Volume": [1000, 1100, 1200, 1300],
        "Dividends": [0.0, 0.0, 0.0, 0.0],
        "Stock Splits": [0.0, 0.0, 0.0, 0.0],
    }
    data.update(overrides)
    return pd.DataFrame(data, index=index)


class FakeTicker:
    """ A yfinance Ticker double. """

    def __init__(self, frame, error=None):
        self.frame = frame
        self.error = error
        self.kwargs: dict = {}

    def history(self, **kwargs):
        self.kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.frame


class FakeClient:
    """ A yfinance module double. """

    def __init__(self, frame=None, error=None):
        self.ticker = FakeTicker(frame if frame is not None else response(), error)
        self.symbol = None

    def Ticker(self, symbol):  # noqa: N802 - mirrors the yfinance API
        self.symbol = symbol
        return self.ticker


@pytest.mark.parametrize(
    ("code", "symbol"),
    [
        ("N225", "^N225"),
        ("GSPC", "^GSPC"),
        ("IXIC", "^IXIC"),
        ("DJI", "^DJI"),
        ("7203", "7203.T"),
        ("6758", "6758.T"),
    ],
)
def test_symbols(code, symbol):
    assert to_symbol(code) == symbol


def test_canonical_columns_in_canonical_order():
    frame = normalize(response(), "7203")
    assert list(frame.columns) == list(CANONICAL_COLUMNS)


def test_action_columns_are_dropped():
    raw = response()
    raw["Capital Gains"] = 0.0
    frame = normalize(raw, "7203")
    for column in ("Dividends", "Stock Splits", "Capital Gains"):
        assert column not in frame.columns


def test_timezone_is_removed_and_the_date_does_not_shift():
    index = pd.to_datetime(
        ["2024-01-04 09:00", "2024-01-05 09:00", "2024-01-08 09:00", "2024-01-09 09:00"]
    ).tz_localize("Asia/Tokyo")
    frame = normalize(response(index=index), "7203")

    assert frame.index.tz is None
    assert list(frame.index.strftime("%Y-%m-%d"))[:2] == ["2024-01-04", "2024-01-05"]
    assert (frame.index.hour == 0).all()


def test_column_multiindex_is_flattened():
    raw = response()
    raw.columns = pd.MultiIndex.from_product([raw.columns, ["7203.T"]])
    frame = normalize(raw, "7203")
    assert list(frame.columns) == list(CANONICAL_COLUMNS)


def test_result_is_sorted_and_on_business_days():
    raw = response().iloc[::-1]
    frame = normalize(raw, "7203")

    assert frame.index.is_monotonic_increasing
    # 4 Jan to 9 Jan 2024 is four business days plus the weekend, which
    # is reindexed in as empty rows the pipeline drops.
    assert len(frame) == 4
    assert list(frame.index.strftime("%Y-%m-%d")) == [
        "2024-01-04",
        "2024-01-05",
        "2024-01-08",
        "2024-01-09",
    ]


def test_a_gap_is_reindexed_as_a_business_day():
    raw = response().drop(index=pd.to_datetime(["2024-01-05", "2024-01-08"]))
    frame = normalize(raw, "7203")

    assert len(frame) == 4
    assert frame.loc["2024-01-05"].isna().all()


def test_duplicate_dates_keep_the_last_row():
    index = pd.to_datetime(["2024-01-04", "2024-01-04", "2024-01-05", "2024-01-08"])
    frame = normalize(response(index=index), "7203")
    assert frame.loc["2024-01-04", "Open"] == 101.0


def test_a_response_without_adjusted_close_is_refused():
    raw = response().drop(columns=["Adj Close"])
    with pytest.raises(DataSourceError, match="Adj Close"):
        normalize(raw, "7203")


def test_an_empty_response_is_a_normal_answer():
    frame = normalize(pd.DataFrame(), "7203")
    assert frame.empty
    assert list(frame.columns) == list(CANONICAL_COLUMNS)


def test_fetch_uses_the_expected_symbol_and_options():
    client = FakeClient()
    source = YahooFinanceSource(client=client)
    source.fetch("7203", START, END)

    assert client.symbol == "7203.T"
    assert client.ticker.kwargs["auto_adjust"] is False
    assert client.ticker.kwargs["interval"] == "1d"
    assert client.ticker.kwargs["start"] == "2024-01-04"
    # The client treats end exclusively; the caller means it inclusively.
    assert client.ticker.kwargs["end"] == "2024-01-10"


def test_fetch_returns_the_canonical_frame():
    source = YahooFinanceSource(client=FakeClient())
    frame = source.fetch("N225", START, END)

    assert list(frame.columns) == list(CANONICAL_COLUMNS)
    assert frame.index.tz is None


def test_a_client_failure_becomes_a_data_source_error():
    client = FakeClient(error=RuntimeError("connection reset"))
    source = YahooFinanceSource(client=client)

    with pytest.raises(DataSourceError, match="7203"):
        source.fetch("7203", START, END)


def test_a_missing_column_is_reported_through_fetch():
    client = FakeClient(frame=response().drop(columns=["Adj Close"]))
    source = YahooFinanceSource(client=client)

    with pytest.raises(DataSourceError, match="Adj Close"):
        source.fetch("7203", START, END)


def test_unknown_source_is_refused():
    with pytest.raises(ConfigurationError, match="Unknown data source"):
        create_source("quandl")
