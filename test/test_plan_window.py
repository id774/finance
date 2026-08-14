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
#  These are the tests of the constraint the Free plan imposes. It
#  publishes nothing newer than twelve weeks ago and keeps two years
#  behind that, and this repository treats both as the specification
#  rather than as a defect to work around. What that has to mean in
#  practice is asserted here: a fetch is never asked for a date the plan
#  cannot answer, a start date older than the plan is raised rather than
#  refused, stored data that already reaches the newest published date
#  is left alone instead of being re-requested every night, and a
#  summary measures staleness against that date rather than against
#  today -- which, if it did not, would drop every stock as stale and
#  write an empty table every evening.
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

from dataclasses import replace
from datetime import date, timedelta

import pandas as pd

from finance.analysis import Analysis, AnalysisRequest
from finance.config import JQuantsSettings
from finance.indicators import SMA_PERIODS
from finance.reporting import SummaryRequest, build_summary
from finance.storage import write_price_csv

TODAY = date(2026, 8, 14)

FREE_PLAN = JQuantsSettings(api_key="test-key", delay_days=84, retention_days=730)


def free(settings):
    """ Return the settings with the Free plan window in place. """
    return replace(settings, jquants=FREE_PLAN, start_date="")


def test_the_window_ends_at_the_newest_published_date():
    assert FREE_PLAN.latest_available(TODAY) == TODAY - timedelta(days=84)


def test_the_window_begins_at_the_oldest_kept_date():
    assert FREE_PLAN.earliest_available(TODAY) == TODAY - timedelta(days=84 + 730)


def test_a_start_date_inside_the_window_is_honoured(settings):
    inside = (TODAY - timedelta(days=200)).isoformat()
    start, end = replace(free(settings), start_date=inside).fetch_window(TODAY)

    assert start.isoformat() == inside
    assert end == FREE_PLAN.latest_available(TODAY)


def test_a_start_date_before_the_window_is_raised_to_it(settings):
    # The value the pipeline used when its source could answer for 2014.
    older = replace(free(settings), start_date="2014-10-01")
    start, _ = older.fetch_window(TODAY)

    assert start == FREE_PLAN.earliest_available(TODAY)


def test_a_plan_without_a_delay_ends_the_window_at_today(settings):
    paid = replace(free(settings), jquants=replace(FREE_PLAN, delay_days=0))
    _, end = paid.fetch_window(TODAY)
    assert end == TODAY


def shifted(frame, last: date):
    """ Return the fixture moved so that its final row falls on a date. """
    moved = frame.copy()
    moved.index = moved.index + (pd.Timestamp(last) - moved.index[-1])
    return moved


def test_a_fetch_is_asked_for_the_window_and_never_beyond_it(
    settings, stub_source, raw_prices
):
    plan = free(settings)
    source = stub_source(shifted(raw_prices, FREE_PLAN.latest_available(TODAY)))
    Analysis(plan, source, today=TODAY).run(
        AnalysisRequest(code="7203", days=60, update=True)
    )

    code, start, end = source.calls[0]
    assert code == "7203"
    assert start == FREE_PLAN.earliest_available(TODAY)
    assert end == FREE_PLAN.latest_available(TODAY)
    assert end < TODAY


def test_stored_data_reaching_the_published_date_is_not_re_requested(
    settings, stub_source, raw_prices
):
    plan = free(settings)
    published = FREE_PLAN.latest_available(TODAY)

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
    plan = free(settings)
    published = FREE_PLAN.latest_available(TODAY)

    shifted(indicator_fixture, published).to_csv(
        plan.data_file("ti_7203.csv"), index_label="Date"
    )
    plan.data_file("stocks.txt").write_text("7203,トヨタ\n", encoding="utf-8")

    result = build_summary(
        plan, SummaryRequest(output="summary.csv", stock_list="stocks.txt"), today=TODAY
    )

    # Twelve weeks old against today, and current against the plan.
    assert result.rows == 1


def test_the_longest_lookback_fits_inside_the_window():
    """
    The longest moving average must be computable within the plan.

    Two years is about 488 trading days; the longest window the
    indicator layer asks for is 200. If a future plan change made this
    false, every long indicator would silently become all-NaN.
    """
    trading_days = (FREE_PLAN.retention_days / 7) * 5
    assert max(SMA_PERIODS) < trading_days
