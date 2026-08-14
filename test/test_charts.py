#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_charts.py: Chart rendering
#
#  Description:
#  Assert what can be asserted about an image without comparing pixels:
#  that a file appears under the expected name, that the axis and
#  complexity switches change what is drawn, that the caption reads as
#  it always has, and that drawing does not disturb the indicator frame
#  it was handed.
#
#  The last of those is the one worth having. The implementation this
#  replaces scaled several series in place for display, mutating the
#  same frame that had just been written to ti_CODE.csv. It happened to
#  be harmless because the write came first, and it would have stopped
#  being harmless the moment those two lines were reordered.
#
#  Test Cases:
#  - Each prefix produces its own file name.
#  - A single axis chart and a two axis chart both render.
#  - Every complexity level renders.
#  - The caption reproduces the historical wording and formatting.
#  - The caption reports the direction arrow from the classification.
#  - A negative change is signed and a positive one carries a plus.
#  - Drawing leaves the caller's indicator frame unchanged.
#  - An empty frame is refused.
#  - A missing indicator column is skipped rather than fatal.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - matplotlib, pandas, pytest
#
#  Version History:
#  v1.0 2026-08-14
#       Ported from the nose suite and extended.
#
########################################################################

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from finance.charts import ChartRenderer
from finance.errors import DataFormatError
from finance.indicators import build_indicator_frame

RUN_DATE = date(2015, 3, 23)


@pytest.fixture()
def drawn(prices):
    """ Return a price window and its indicator frame. """
    return prices, build_indicator_frame(prices).stock


@pytest.mark.parametrize("prefix", ["chart", "long", "short", "test"])
def test_each_prefix_writes_its_own_file(drawn, data_dir, prefix):
    stock, indicators = drawn
    renderer = ChartRenderer("N225", "日経平均株価")

    path = renderer.plot(stock, indicators, prefix, data_dir, 0, 5000, today=RUN_DATE)

    assert path.name == "{0}_N225.png".format(prefix)
    assert path.is_file()
    assert path.stat().st_size > 0


@pytest.mark.parametrize(
    ("axis", "complexity"), [(1, 1), (1, 3), (2, 1), (2, 2), (2, 3)]
)
def test_every_axis_and_complexity_combination_renders(drawn, data_dir, axis, complexity):
    stock, indicators = drawn
    renderer = ChartRenderer("N225", "日経平均株価")

    path = renderer.plot(
        stock,
        indicators,
        "chart",
        data_dir,
        1,
        19000,
        axis=axis,
        complexity=complexity,
        today=RUN_DATE,
    )
    assert path.is_file()


def test_caption_reproduces_the_historical_wording(drawn):
    stock, _ = drawn
    renderer = ChartRenderer("N225", "日経平均株価")

    caption = renderer.caption(stock, classified=1, predicted=19125, today=RUN_DATE)

    assert caption.startswith("日経平均株価(N225)  2015/03/23\n")
    assert "終値:19,560" in caption
    assert "出来高:133,400" in caption
    assert "最高:" in caption and "最安:" in caption
    assert "分類器予測:↑" in caption
    assert "回帰分析:19,125" in caption


def test_caption_reports_a_falling_classification(drawn):
    stock, _ = drawn
    renderer = ChartRenderer("N225", "日経平均株価")
    caption = renderer.caption(stock, classified=0, predicted=19125, today=RUN_DATE)
    assert "分類器予測:↓" in caption


def test_caption_signs_the_change(drawn):
    stock, _ = drawn
    renderer = ChartRenderer("N225", "日経平均株価")

    rising = renderer.caption(stock, 1, 1, today=RUN_DATE)
    assert "(+84," in rising

    falling_stock = stock.copy()
    falling_stock.loc[falling_stock.index[-1], "Adj Close"] = 19000.0
    falling = renderer.caption(falling_stock, 1, 1, today=RUN_DATE)
    assert "(-476," in falling


def test_caption_uses_the_same_ratio_as_the_summaries(drawn):
    from finance.aggregation import change_ratio

    stock, _ = drawn
    renderer = ChartRenderer("N225", "日経平均株価")
    caption = renderer.caption(stock, 1, 1, today=RUN_DATE)

    close = int(stock.iloc[-1]["Adj Close"])
    change = close - int(stock.iloc[-2]["Adj Close"])
    assert "{0}%".format(change_ratio(change, close)) in caption


def test_caption_needs_two_rows(drawn):
    stock, _ = drawn
    renderer = ChartRenderer("N225", "日経平均株価")
    with pytest.raises(DataFormatError, match="two rows"):
        renderer.caption(stock.iloc[-1:], 1, 1, today=RUN_DATE)


def test_drawing_does_not_mutate_the_indicator_frame(drawn, data_dir):
    stock, indicators = drawn
    before = indicators.copy(deep=True)

    ChartRenderer("N225", "日経平均株価").plot(
        stock, indicators, "chart", data_dir, 1, 19000, today=RUN_DATE
    )

    pd.testing.assert_frame_equal(indicators, before)


def test_an_empty_frame_is_refused(drawn, data_dir):
    stock, indicators = drawn
    with pytest.raises(DataFormatError, match="no price rows"):
        ChartRenderer("N225", "日経平均株価").plot(
            stock.iloc[0:0], indicators, "chart", data_dir, 1, 1, today=RUN_DATE
        )


def test_a_missing_indicator_column_is_skipped(drawn, data_dir):
    stock, indicators = drawn
    reduced = indicators.drop(columns=["upperband", "lowerband", "sar"])

    path = ChartRenderer("N225", "日経平均株価").plot(
        stock, reduced, "chart", data_dir, 1, 19000, today=RUN_DATE
    )
    assert path.is_file()


def test_a_missing_font_does_not_stop_the_chart(drawn, data_dir):
    stock, indicators = drawn
    renderer = ChartRenderer("N225", "日経平均株価", font_path="/nonexistent/font.ttf")

    assert renderer.font_properties is None
    assert renderer.plot(
        stock, indicators, "chart", data_dir, 1, 19000, today=RUN_DATE
    ).is_file()
