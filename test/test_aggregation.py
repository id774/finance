#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_aggregation.py: Summary table construction
#
#  Description:
#  Assert what a summary row contains, how it is sorted, and which
#  stocks are left out of one.
#
#  The staleness filter and the ratio formula both get their own test.
#  Neither is obvious from reading the code, and both would be easy to
#  "fix" into something that quietly restates every figure the operator
#  has on file.
#
#  Test Cases:
#  - A trend summary carries nine values in contract order.
#  - A screening summary substitutes its key for the model outputs.
#  - The ratio is the historical one plus change over close.
#  - Values are truncated, not rounded.
#  - The change spans the requested number of rows.
#  - A stock whose last row predates the cutoff is dropped.
#  - No current stock yields an empty frame rather than an error.
#  - Sorting honours the key and the direction.
#  - An unknown sort key is refused.
#  - A stock with too few rows for the span is skipped, not fatal.
#  - The legacy expectation that a directory with no matching files
#    aggregates to an empty result.
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

from datetime import date, timedelta

import pandas as pd
import pytest

from finance.aggregation import Aggregator, change_ratio, summary_columns
from finance.analysis import load_indicator_frames
from finance.errors import DataFormatError
from finance.stocklist import StockEntry

RUN_DATE = date(2026, 8, 14)


def make_frame(closes, last_date=RUN_DATE, classified=1, predicted=2500, rsi=55.7):
    """ Build an indicator frame ending on the given date. """
    index = pd.date_range(end=pd.Timestamp(last_date), periods=len(closes), freq="B")
    frame = pd.DataFrame(
        {
            "Open": [c - 5 for c in closes],
            "High": [c + 10 for c in closes],
            "Low": [c - 12 for c in closes],
            "Close": closes,
            "Volume": [100_000] * len(closes),
            "Adj Close": closes,
            "rsi14": [rsi] * len(closes),
            "rsi9": [rsi] * len(closes),
        },
        index=index,
    )
    frame["classified"] = None
    frame["predicted"] = None
    frame.loc[frame.index[-1], "classified"] = classified
    frame.loc[frame.index[-1], "predicted"] = predicted
    return frame


def test_trend_summary_carries_the_contract_columns():
    frames = {("7203", "トヨタ"): make_frame([2000.0, 2050.0, 2100.0])}
    table = Aggregator(frames).summarize(span=1, as_of=RUN_DATE)

    assert list(table.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Change",
        "Ratio",
        "Trend",
        "Pred",
        "Name",
    ]
    assert list(table.index) == ["7203"]


def test_screening_summary_substitutes_its_key():
    frames = {("7203", "トヨタ"): make_frame([2000.0, 2050.0, 2100.0], rsi=68.4)}
    table = Aggregator(frames).summarize(
        span=1, sortkey="rsi14", screening_key="rsi14", as_of=RUN_DATE
    )

    assert list(table.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Change",
        "Ratio",
        "rsi14",
        "Name",
    ]
    # Truncated, matching every other value in the table.
    assert table.loc["7203", "rsi14"] == 68


def test_summary_columns_helper_matches_the_layouts():
    assert summary_columns(None)[-3:] == ("Trend", "Pred", "Name")
    assert summary_columns("rsi9")[-2:] == ("rsi9", "Name")


def test_row_values_are_truncated_not_rounded():
    frames = {("7203", "トヨタ"): make_frame([2000.9, 2050.9, 2100.9])}
    table = Aggregator(frames).summarize(span=1, as_of=RUN_DATE)

    assert table.loc["7203", "Close"] == 2100
    assert table.loc["7203", "High"] == 2110
    assert table.loc["7203", "Low"] == 2088


def test_change_spans_the_requested_rows():
    closes = [1000.0, 1100.0, 1200.0, 1300.0, 1400.0]
    frames = {("7203", "トヨタ"): make_frame(closes)}

    one = Aggregator(frames).summarize(span=1, as_of=RUN_DATE)
    assert one.loc["7203", "Change"] == 100

    three = Aggregator(frames).summarize(span=3, as_of=RUN_DATE)
    assert three.loc["7203", "Change"] == 300


def test_ratio_keeps_its_historical_formula():
    # One plus the change over the close, not the change over the close.
    # Preserved so that data/history stays comparable with today.
    assert change_ratio(100, 2000) == round(101 / 2000 * 100, 2)
    assert change_ratio(-50, 1000) == round(-49 / 1000 * 100, 2)

    frames = {("7203", "トヨタ"): make_frame([2000.0, 2100.0])}
    table = Aggregator(frames).summarize(span=1, as_of=RUN_DATE)
    assert table.loc["7203", "Ratio"] == change_ratio(100, 2100)


def test_a_stale_stock_is_dropped():
    stale = make_frame([100.0, 110.0], last_date=RUN_DATE - timedelta(days=40))
    fresh = make_frame([200.0, 220.0])
    frames = {("1111", "古い"): stale, ("2222", "新しい"): fresh}

    table = Aggregator(frames).summarize(span=1, as_of=RUN_DATE)
    assert list(table.index) == ["2222"]


def test_a_stock_just_inside_the_cutoff_is_kept():
    recent = make_frame([100.0, 110.0], last_date=RUN_DATE - timedelta(days=9))
    table = Aggregator({("1111", "ぎりぎり"): recent}).summarize(span=1, as_of=RUN_DATE)
    assert list(table.index) == ["1111"]


def test_no_current_stock_yields_an_empty_frame():
    stale = make_frame([100.0, 110.0], last_date=RUN_DATE - timedelta(days=90))
    table = Aggregator({("1111", "古い"): stale}).summarize(span=1, as_of=RUN_DATE)
    assert table.empty


def test_sorting_honours_key_and_direction():
    frames = {
        ("1111", "低い"): make_frame([1000.0, 1001.0]),
        ("2222", "高い"): make_frame([1000.0, 1500.0]),
    }

    descending = Aggregator(frames).summarize(span=1, sortkey="Ratio", as_of=RUN_DATE)
    assert list(descending.index) == ["2222", "1111"]

    ascending = Aggregator(frames).summarize(
        span=1, sortkey="Ratio", ascending=True, as_of=RUN_DATE
    )
    assert list(ascending.index) == ["1111", "2222"]


def test_unknown_sort_key_is_refused():
    frames = {("7203", "トヨタ"): make_frame([2000.0, 2100.0])}
    with pytest.raises(DataFormatError, match="Cannot sort by"):
        Aggregator(frames).summarize(span=1, sortkey="nonexistent", as_of=RUN_DATE)


def test_a_stock_with_too_few_rows_is_skipped_not_fatal():
    frames = {
        ("1111", "短い"): make_frame([1000.0, 1010.0]),
        ("2222", "十分"): make_frame([1000.0 + i for i in range(20)]),
    }
    table = Aggregator(frames).summarize(span=10, as_of=RUN_DATE)
    assert list(table.index) == ["2222"]


def test_a_missing_screening_column_skips_the_stock():
    frame = make_frame([1000.0, 1010.0]).drop(columns=["rsi14"])
    table = Aggregator({("1111", "欠落"): frame}).summarize(
        span=1, sortkey=None, screening_key="rsi14", as_of=RUN_DATE
    )
    assert table.empty


def test_a_directory_without_indicator_files_aggregates_to_nothing(settings):
    """ The expectation the legacy test_aggregate.py asserted. """
    entries = [StockEntry("6758", "ソニー"), StockEntry("7203", "トヨタ")]
    frames = load_indicator_frames(settings, entries)
    assert frames == {}
    assert Aggregator(frames).summarize(as_of=RUN_DATE).empty


def test_a_stock_without_a_stored_file_is_left_out_rather_than_raised_on(
    settings, indicator_fixture
):
    path = settings.data_file("ti_7203.csv")
    indicator_fixture.to_csv(path, index_label="Date")

    entries = [StockEntry("6758", "ソニー"), StockEntry("7203", "トヨタ")]
    frames = load_indicator_frames(settings, entries)
    assert list(frames) == [("7203", "トヨタ")]
