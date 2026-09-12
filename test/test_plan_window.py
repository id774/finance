#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_plan_window.py: The subscribed plan's data window
#
#  Description:
#  Assert that the delay and the retention of the subscribed J-Quants
#  plan decide the dates a run may ask for, and that the rest of the
#  pipeline behaves correctly at the edges of that window.
#
#  These tests use an explicit publication-delay and retention fixture.
#  Its values are test inputs and program defaults, not assertions about
#  current provider plan terms. The behavior under that configured
#  window is asserted here: a fetch is never asked for a date outside
#  the window, a start date older than the window is raised to its lower
#  bound, stored data that reaches the newest configured date is left
#  alone instead of being re-requested every night, and a summary
#  measures staleness against that date rather than against today.
#
#  Test Cases:
#  - The window ends at the newest date the plan publishes.
#  - The window begins at the oldest date the plan keeps.
#  - A configured start date inside the window is honoured.
#  - A configured start date before the window is raised to it.
#  - A plan without a delay ends the window at today.
#  - A fetch is asked for the window and never beyond it.
#  - Stored data reaching the newest published date is not re-requested.
#  - Staleness is measured against the newest published date.
#  - The lookback the longest indicator needs fits inside the window.
#  - The configured minimum retention window covers that same lookback.
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
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pandas as pd

from finance.analysis import Analysis, AnalysisRequest
from finance.config import MIN_RETENTION_DAYS, JQuantsSettings
from finance.indicators import SMA_PERIODS
from finance.reporting import SummaryRequest, build_summary
from finance.storage import write_price_csv

TODAY = date(2026, 8, 14)

TEST_PLAN = JQuantsSettings(api_key="test-key", delay_days=84, retention_days=730)


def with_test_plan(settings):
    """ Return the settings with the test plan window in place. """
    return replace(settings, jquants=TEST_PLAN, start_date="")


def test_the_window_ends_at_the_newest_published_date():
    assert TEST_PLAN.latest_available(TODAY) == TODAY - timedelta(days=84)


def test_the_window_begins_at_the_oldest_kept_date():
    assert TEST_PLAN.earliest_available(TODAY) == TODAY - timedelta(days=84 + 730)


def test_a_start_date_inside_the_window_is_honoured(settings):
    inside = (TODAY - timedelta(days=200)).isoformat()
    start, end = replace(with_test_plan(settings), start_date=inside).fetch_window(TODAY)

    assert start.isoformat() == inside
    assert end == TEST_PLAN.latest_available(TODAY)


def test_a_start_date_before_the_window_is_raised_to_it(settings):
    # The value the pipeline used when its source could answer for 2014.
    older = replace(with_test_plan(settings), start_date="2014-10-01")
    start, _ = older.fetch_window(TODAY)

    assert start == TEST_PLAN.earliest_available(TODAY)


def test_a_plan_without_a_delay_ends_the_window_at_today(settings):
    no_delay = replace(
        with_test_plan(settings), jquants=replace(TEST_PLAN, delay_days=0)
    )
    _, end = no_delay.fetch_window(TODAY)
    assert end == TODAY


def shifted(frame, last: date):
    """ Return the fixture moved so that its final row falls on a date. """
    moved = frame.copy()
    moved.index = moved.index + (pd.Timestamp(last) - moved.index[-1])
    return moved


def test_a_fetch_is_asked_for_the_window_and_never_beyond_it(
    settings, stub_source, raw_prices
):
    plan = with_test_plan(settings)
    source = stub_source(shifted(raw_prices, TEST_PLAN.latest_available(TODAY)))
    Analysis(plan, source, today=TODAY).run(
        AnalysisRequest(code="7203", days=60, update=True)
    )

    code, start, end = source.calls[0]
    assert code == "7203"
    assert start == TEST_PLAN.earliest_available(TODAY)
    assert end == TEST_PLAN.latest_available(TODAY)
    assert end < TODAY


def test_stored_data_reaching_the_published_date_is_not_re_requested(
    settings, stub_source, raw_prices
):
    plan = with_test_plan(settings)
    published = TEST_PLAN.latest_available(TODAY)

    # Stored history whose last row is the newest date the plan has.
    write_price_csv(shifted(raw_prices, published), plan.data_file("stock_7203.csv"))

    source = stub_source(raw_prices)
    Analysis(plan, source, today=TODAY).run(
        AnalysisRequest(code="7203", days=60, update=True, csvfile="stock_7203.csv")
    )

    assert source.calls == []


def test_staleness_is_measured_against_the_published_date(
    settings, stub_source, raw_prices, indicator_fixture
):
    plan = with_test_plan(settings)
    published = TEST_PLAN.latest_available(TODAY)

    shifted(indicator_fixture, published).to_csv(
        plan.data_file("ti_7203.csv"), index_label="Date"
    )
    plan.data_file("stocks.txt").write_text("7203,トヨタ\n", encoding="utf-8")

    result = build_summary(
        plan, SummaryRequest(output="summary.csv", stock_list="stocks.txt"), today=TODAY
    )

    # The delayed fixture is current against the configured plan window.
    assert result.rows == 1


def test_the_longest_lookback_fits_inside_the_window():
    """
    The longest moving average must be computable within the plan.

    The configured retention window is converted to an approximate
    weekday count. The longest indicator window must fit inside it; if
    a future configuration change made this false, every long indicator
    would silently become all-NaN.
    """
    trading_days = (TEST_PLAN.retention_days / 7) * 5
    assert max(SMA_PERIODS) < trading_days


def test_minimum_retention_window_covers_the_longest_required_lookback():
    """
    MIN_RETENTION_DAYS must be the smallest window that still fits the
    longest indicator lookback, so a configuration right at the minimum
    is usable and one day short is provably not.
    """
    assert max(SMA_PERIODS) < (MIN_RETENTION_DAYS / 7) * 5
    assert not max(SMA_PERIODS) < ((MIN_RETENTION_DAYS - 1) / 7) * 5
