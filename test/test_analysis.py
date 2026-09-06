#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_analysis.py: The per stock pipeline
#
#  Description:
#  Assert what one run of the pipeline writes, what it leaves alone, and
#  what it does when a stock fails.
#
#  The behaviours that matter most here are the ones a refactor would
#  quietly drop: that a run without -u writes no data file, that a run
#  finding no new prices leaves the indicator file and the models
#  untouched, and that one failing stock does not end a list run.
#
#  Test Cases:
#  - A run reproduces the indicator value the legacy suite asserted.
#  - The requested window length is honoured.
#  - A chart is written under the prefix the window selects.
#  - Without update, no CSV is written and no model is persisted.
#  - With update, both CSVs are written and both models are persisted.
#  - A run finding no new prices writes no indicator file.
#  - Stored rows win over fetched rows for the same date.
#  - The window length selects the chart prefix.
#  - A failing stock is reported and the rest of the list continues.
#  - An empty price history is refused.
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

from finance.analysis import Analysis, AnalysisRequest, run_many
from finance.errors import DataFormatError, DataSourceError

CODE = "N225"
RUN_DATE = date(2015, 3, 23)


@pytest.fixture()
def stored(settings, raw_prices):
    """ Write the fixture prices where the pipeline will look for them. """
    path = settings.data_file("stock_{0}.csv".format(CODE))
    raw_prices.to_csv(path, index_label="Date")
    return path


def make_analysis(settings, stub_source, frame=None):
    """ Build a pipeline bound to a stub price source. """
    source = stub_source(frame)
    return Analysis(settings, source, today=RUN_DATE), source


def test_run_reproduces_the_legacy_indicator_value(settings, stub_source, stored):
    analysis, _ = make_analysis(settings, stub_source)
    request = AnalysisRequest(code=CODE, name="日経平均株価", days=180, csvfile=stored.name)

    result = analysis.run(request)

    value = result.indicator_frame.loc["2015-03-20", "sma25"]
    assert round(float(value), 2) == 18791.39


def test_run_honours_the_window_length(settings, stub_source, stored):
    analysis, _ = make_analysis(settings, stub_source)
    result = analysis.run(AnalysisRequest(code=CODE, days=180, csvfile=stored.name))
    assert result.rows == 180


def test_a_zero_window_uses_every_row(settings, stub_source, stored, raw_prices):
    analysis, _ = make_analysis(settings, stub_source)
    result = analysis.run(AnalysisRequest(code=CODE, days=0, csvfile=stored.name))
    assert result.rows == len(raw_prices)


def test_a_chart_is_written(settings, stub_source, stored):
    analysis, _ = make_analysis(settings, stub_source)
    result = analysis.run(AnalysisRequest(code=CODE, days=180, csvfile=stored.name))

    assert result.chart_path.name == "chart_N225.png"
    assert result.chart_path.is_file()
    assert result.chart_path.stat().st_size > 0


@pytest.mark.parametrize(
    ("days", "filename"),
    [(600, "long_N225.png"), (240, "chart_N225.png"), (60, "short_N225.png")],
)
def test_the_window_selects_the_chart(settings, stub_source, stored, days, filename):
    analysis, _ = make_analysis(settings, stub_source)
    result = analysis.run(AnalysisRequest(code=CODE, days=days, csvfile=stored.name))
    assert result.chart_path.name == filename


def test_without_update_nothing_is_written(settings, stub_source, stored):
    analysis, source = make_analysis(settings, stub_source)
    result = analysis.run(
        AnalysisRequest(code=CODE, days=180, csvfile=stored.name, update=False)
    )

    assert result.wrote_indicators is False
    assert not settings.data_file("ti_N225.csv").exists()
    assert not (settings.model_dir / "clf_N225.pickle").exists()
    assert not (settings.model_dir / "reg_N225.pickle").exists()
    # No fetch either: a chart-only run must not reach the network.
    assert source.calls == []


def test_with_update_both_files_and_both_models_are_written(
    settings, stub_source, stored, raw_prices
):
    # One new business day beyond the stored history.
    extra = raw_prices.iloc[[-1]].copy()
    extra.index = pd.DatetimeIndex([pd.Timestamp("2015-03-23")])
    analysis, source = make_analysis(settings, stub_source, extra)

    result = analysis.run(
        AnalysisRequest(code=CODE, days=180, csvfile=stored.name, update=True)
    )

    assert result.wrote_indicators is True
    assert settings.data_file("ti_N225.csv").is_file()
    assert settings.data_file("stock_N225.csv").is_file()
    assert (settings.model_dir / "clf_N225.pickle").is_file()
    assert (settings.model_dir / "reg_N225.pickle").is_file()
    assert source.calls, "an updating run must fetch"


def test_no_new_prices_leaves_the_indicator_file_alone(settings, stub_source, stored):
    analysis, source = make_analysis(settings, stub_source)
    result = analysis.run(
        AnalysisRequest(code=CODE, days=180, csvfile=stored.name, update=True)
    )

    assert source.calls, "an updating run must try to fetch"
    assert result.wrote_indicators is False
    assert not settings.data_file("ti_N225.csv").exists()


def test_stored_rows_win_over_fetched_rows(settings, stub_source, stored, raw_prices):
    # The source answers with a different price for a date already
    # stored. combine_first must keep the stored one, which is what
    # protects historical figures from a changed adjustment basis.
    overlap = raw_prices.iloc[[-1]].copy()
    overlap["Adj Close"] = 1.0
    later = raw_prices.iloc[[-1]].copy()
    later.index = pd.DatetimeIndex([pd.Timestamp("2015-03-23")])
    fetched = pd.concat([overlap, later])

    analysis, _ = make_analysis(settings, stub_source, fetched)
    analysis.run(AnalysisRequest(code=CODE, days=180, csvfile=stored.name, update=True))

    written = pd.read_csv(
        settings.data_file("stock_N225.csv"), index_col=0, parse_dates=True
    )
    assert float(written.loc["2015-03-20", "Adj Close"]) == 19560.22


def test_the_model_outputs_land_on_the_last_row(settings, stub_source, stored):
    analysis, _ = make_analysis(settings, stub_source)
    result = analysis.run(AnalysisRequest(code=CODE, days=180, csvfile=stored.name))

    frame = result.indicator_frame
    assert frame["classified"].notna().sum() == 1
    assert frame["predicted"].notna().sum() == 1
    assert result.classified in (0, 1)
    assert result.predicted > 0


def test_a_missing_stored_file_falls_back_to_fetching(settings, stub_source, raw_prices):
    analysis, source = make_analysis(settings, stub_source, raw_prices)
    result = analysis.run(
        AnalysisRequest(code=CODE, days=180, csvfile="stock_N225.csv", update=True)
    )

    # The whole history is requested from the configured start date, so
    # the run covers whatever the source has rather than the window.
    assert source.calls == [(CODE, date(2014, 10, 1), RUN_DATE)]
    assert result.rows > 0
    assert settings.data_file("stock_N225.csv").is_file()


def test_an_empty_history_is_refused(settings, stub_source):
    analysis, _ = make_analysis(settings, stub_source)
    with pytest.raises(DataFormatError, match="No price data"):
        analysis.run(AnalysisRequest(code="9999", days=180))


def test_one_failing_stock_does_not_end_a_list_run(settings, stub_source, stored):
    class FailingSource:
        """ Fails for one code and answers empty for the rest. """

        def fetch(self, code, start, end):
            if code == "BROKEN":
                raise DataSourceError("delisted")
            return pd.DataFrame()

    analysis = Analysis(settings, FailingSource(), today=RUN_DATE)
    requests = [
        AnalysisRequest(code="BROKEN", days=180),
        AnalysisRequest(code=CODE, days=180, csvfile=stored.name),
    ]

    results, failures = run_many(analysis, requests)

    assert [r.code for r in results] == [CODE]
    assert [code for code, _ in failures] == ["BROKEN"]
    assert isinstance(failures[0][1], DataSourceError)


def test_a_run_of_only_failures_reports_them_all(settings):
    class FailingSource:
        def fetch(self, code, start, end):
            raise DataSourceError("no route to host")

    analysis = Analysis(settings, FailingSource(), today=RUN_DATE)
    results, failures = run_many(
        analysis, [AnalysisRequest(code="1111"), AnalysisRequest(code="2222")]
    )

    assert results == []
    assert [code for code, _ in failures] == ["1111", "2222"]


def test_an_unreadable_model_is_replaced_rather_than_fatal(settings, stub_source, stored):
    settings.model_dir.mkdir(parents=True, exist_ok=True)
    (settings.model_dir / "clf_N225.pickle").write_bytes(b"not a pickle")

    analysis, _ = make_analysis(settings, stub_source)
    result = analysis.run(AnalysisRequest(code=CODE, days=180, csvfile=stored.name))
    assert result.classified in (0, 1)
