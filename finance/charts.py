#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/charts.py: Chart rendering
#
#  Description:
#  Draw the PNG charts finance-dashboard displays: a candlestick price
#  panel with moving averages, Bollinger bands and the parabolic SAR,
#  captioned with the closing figures and the two model outputs. When
#  axis=2 an oscillator panel carrying RSI, MFI, stochastics and the
#  rest is added below it; axis=1 draws the price panel alone.
#
#  This is the one module that could not be ported by changing API
#  calls. The old implementation registered a subclass of a private
#  pandas plotting class into three private pandas registries and drew
#  its candles with matplotlib.finance.candlestick_ochl. The registries
#  are gone from pandas and the module was deleted from matplotlib in
#  3.0, so the drawing is done here with matplotlib primitives instead.
#
#  What that rewrite preserves, deliberately and in full: the file
#  names, the figure size, every series drawn, the colours, the labels,
#  the legend placement, the axis and complexity switches, the caption
#  text and the number formatting in it. What it cannot preserve is
#  pixel identity, which was never asserted and is not asserted now.
#
#  Candles are drawn against row positions rather than dates, and the
#  ticks are labelled with the dates of those positions. That reproduces
#  the axis the old chart had, where consecutive business days sit
#  side by side and a weekend leaves no gap.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - matplotlib, pandas
#
#  Version History:
#  v1.0 2026-08-14
#       Draw with matplotlib primitives instead of the removed pandas
#       and matplotlib internals.
#
########################################################################

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path

import matplotlib

matplotlib.use("agg")

import matplotlib.pyplot as plt  # noqa: E402 - the backend must be set before pyplot
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter  # noqa: E402

from finance.errors import DataFormatError, StorageError  # noqa: E402

FIGURE_SIZE = (12.80, 10.24)
CANDLE_WIDTH = 0.6
CANDLE_UP_COLOR = "r"
CANDLE_DOWN_COLOR = "b"

OSCILLATOR_TICKS = (0, 25, 50, 75, 100)
X_TICK_COUNT = 8

# The prefixes finance-dashboard builds its <img> sources from, and the
# windows that select them. A window longer than LONG_WINDOW_DAYS is a
# long chart; one no longer than SHORT_WINDOW_DAYS is a short chart.
LONG_PREFIX = "long"
SHORT_PREFIX = "short"
DEFAULT_PREFIX = "chart"
LONG_WINDOW_DAYS = 300
SHORT_WINDOW_DAYS = 60

logger = logging.getLogger(__name__)


def chart_prefix(days: int) -> str:
    """
    Return the file name prefix a window length selects.

    The mapping is a contract: finance-dashboard asks for chart_CODE.png,
    long_CODE.png or short_CODE.png by view, and nothing writes those
    names but this rule.
    """
    if days > LONG_WINDOW_DAYS:
        return LONG_PREFIX
    if days <= SHORT_WINDOW_DAYS:
        return SHORT_PREFIX
    return DEFAULT_PREFIX


def chart_filename(prefix: str, code: str) -> str:
    """ Return the PNG file name of one chart. """
    return "{0}_{1}.png".format(prefix, code)


def _load_font(font_path: str):
    """
    Return font properties for the caption, or None to use the default.

    A missing font is a warning rather than an error. The caption is in
    Japanese and will render as boxes without it, but a chart with an
    unreadable caption is still worth more to the nightly run than no
    chart at all.
    """
    from matplotlib import font_manager

    if font_path and os.path.exists(font_path):
        return font_manager.FontProperties(fname=font_path)
    logger.warning("Caption font not found at %s; Japanese text may not render", font_path)
    return None


def draw_candlesticks(
    ax, positions: np.ndarray, frame: pd.DataFrame, width: float = CANDLE_WIDTH
) -> None:
    """
    Draw an open-high-low-close candlestick series.

    Reproduces the geometry of the removed matplotlib.finance
    candlestick_ochl: a thin wick from low to high and a filled body
    between open and close, coloured by the direction of the day.
    """
    offset = width / 2.0
    opens = frame["Open"].to_numpy(dtype="f8")
    highs = frame["High"].to_numpy(dtype="f8")
    lows = frame["Low"].to_numpy(dtype="f8")
    closes = frame["Close"].to_numpy(dtype="f8")

    for position, open_, high, low, close in zip(
        positions, opens, highs, lows, closes, strict=True
    ):
        if not np.isfinite([open_, high, low, close]).all():
            continue
        if close >= open_:
            color = CANDLE_UP_COLOR
            lower = open_
            height = close - open_
        else:
            color = CANDLE_DOWN_COLOR
            lower = close
            height = open_ - close
        ax.add_line(
            Line2D(
                xdata=(position, position),
                ydata=(low, high),
                color=color,
                linewidth=0.5,
                antialiased=True,
            )
        )
        ax.add_patch(
            Rectangle(
                xy=(position - offset, lower),
                width=width,
                height=height,
                facecolor=color,
                edgecolor=color,
            )
        )
    ax.autoscale_view()


def _format_x_axis(ax, index: pd.DatetimeIndex) -> None:
    """ Label the positional x axis with the dates of the rows it stands for. """
    count = len(index)
    if count == 0:
        return
    step = max(1, count // X_TICK_COUNT)
    positions = list(range(0, count, step))

    def label(value, _position):
        row = int(round(value))
        if 0 <= row < count:
            return index[row].strftime("%Y-%m")
        return ""

    ax.xaxis.set_major_locator(FixedLocator(positions))
    ax.xaxis.set_major_formatter(FuncFormatter(label))


class ChartRenderer:
    """ Draw and save the chart of one stock. """

    def __init__(self, code: str, name: str, font_path: str = "") -> None:
        """
        Args:
            code: Stock code, used in the file name and the caption.
            name: Display name shown in the caption.
            font_path: TrueType font for the Japanese caption.
        """
        self.code = code
        self.name = name
        self.font_properties = _load_font(font_path)

    def plot(
        self,
        stock: pd.DataFrame,
        indicators: pd.DataFrame,
        prefix: str,
        output_dir: str | os.PathLike[str],
        classified: int,
        predicted: int,
        axis: int = 2,
        complexity: int = 3,
        today: date | None = None,
    ) -> Path:
        """
        Draw one chart and write it as a PNG.

        Args:
            stock: The OHLCV frame of the window being charted.
            indicators: The indicator frame covering the same rows.
            prefix: File name prefix, from chart_prefix().
            output_dir: Directory the PNG is written to.
            classified: The trend classification, 1 for up and 0 for down.
            predicted: The predicted price shown in the caption.
            axis: 1 draws the price panel alone, 2 adds the oscillator
                panel below it.
            complexity: 1 to 3, how many series each panel carries.
            today: The date printed in the caption. Injected for tests.

        Returns:
            The path written.

        Raises:
            DataFormatError: The frames carry no rows or lack a column
                the chart needs.
            StorageError: The PNG cannot be written.
        """
        if stock.empty:
            raise DataFormatError("Cannot chart {0}: no price rows".format(self.code))

        # The indicator frame is drawn from, not written to. Display
        # scalings below shift several series onto the shared 0-100
        # panel, and a copy keeps that out of the caller's frame, which
        # is the same object that was written to ti_CODE.csv.
        #
        # It is reindexed onto the price rows rather than assumed to
        # match them. The indicator frame is built from trading days
        # while a price window may still carry the empty rows a business
        # day reindex left behind, and the two are aligned by date, as
        # they were when pandas did the plotting.
        index = pd.DatetimeIndex(stock.index)
        indicators = indicators.reindex(index)
        positions = np.arange(len(stock))

        figure = plt.figure(figsize=FIGURE_SIZE)
        try:
            price_axes = figure.add_subplot(2, 1, 1) if axis >= 2 else figure.add_subplot(1, 1, 1)
            self._plot_price_panel(
                price_axes, positions, stock, indicators, axis, complexity
            )
            _format_x_axis(price_axes, index)

            if axis >= 2:
                price_axes.legend(
                    loc="upper center",
                    bbox_to_anchor=(0.36, 1.228),
                    ncol=complexity + 1,
                    fancybox=False,
                    shadow=False,
                )
                oscillator_axes = figure.add_subplot(2, 1, 2)
                self._plot_oscillator_panel(
                    oscillator_axes, positions, indicators, complexity
                )
                _format_x_axis(oscillator_axes, index)
                caption_axes = oscillator_axes
            else:
                caption_axes = price_axes

            self._set_caption(caption_axes, stock, classified, predicted, today)
            if axis >= 2:
                caption_axes.legend(
                    loc="upper center",
                    bbox_to_anchor=(0.48, 1.23),
                    ncol=complexity + 3,
                    fancybox=False,
                    shadow=False,
                )
            else:
                caption_axes.legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, 1.105),
                    ncol=complexity + 2,
                    fancybox=False,
                    shadow=False,
                )

            target = Path(output_dir) / chart_filename(prefix, self.code)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                figure.savefig(target)
            except OSError as exc:
                raise StorageError("Chart could not be written: {0}".format(target)) from exc
        finally:
            plt.close(figure)

        logger.debug("Wrote chart %s", target)
        return target

    def _series(self, indicators: pd.DataFrame, column: str) -> np.ndarray | None:
        """ Return an indicator column as an array, or None when it is absent. """
        if column not in indicators.columns:
            logger.warning("Chart for %s omits %s: column absent", self.code, column)
            return None
        return indicators[column].to_numpy(dtype="f8")

    def _line(self, ax, positions, indicators, column, label, color, linestyle="-") -> None:
        """ Draw one indicator series if it is present. """
        values = self._series(indicators, column)
        if values is None:
            return
        ax.plot(positions, values, label=label, color=color, linestyle=linestyle)

    def _plot_price_panel(
        self,
        ax,
        positions: np.ndarray,
        stock: pd.DataFrame,
        indicators: pd.DataFrame,
        axis: int,
        complexity: int,
    ) -> None:
        """ Draw the candlesticks and the trend series above them. """
        if complexity >= 2:
            self._line(ax, positions, indicators, "ewma5", "MA5", "k")
        self._line(ax, positions, indicators, "ewma25", "MA25", "g")
        self._line(ax, positions, indicators, "ewma50", "MA50", "m")
        self._line(ax, positions, indicators, "ewma75", "MA75", "r")
        if complexity < 2:
            self._line(ax, positions, indicators, "ewma200", "MA200", "k")
        if complexity >= 3:
            self._line(ax, positions, indicators, "upperband", "UPPER", "c")
            self._line(ax, positions, indicators, "lowerband", "LOWER", "y")
        if complexity >= 2:
            self._line(ax, positions, indicators, "sar", "SAR", "#FF0088", linestyle=":")
        if axis == 1:
            self._line(
                ax, positions, indicators, "v_rate_p", "VOLUME", "#444444", linestyle=":"
            )
        draw_candlesticks(ax, positions, stock)
        ax.grid(True)

    def _plot_oscillator_panel(
        self, ax, positions: np.ndarray, indicators: pd.DataFrame, complexity: int
    ) -> None:
        """
        Draw the oscillator panel.

        Several series are shifted or scaled so that they share the
        0-100 axis: the rates of change are lifted by 50 around their
        zero, Williams %R by 100 from its negative range, and the
        volatility ratio by five so that a normal day is visible against
        the oscillators. These are display transforms only; ti_CODE.csv
        holds the unscaled values.
        """
        if "vl" in indicators.columns:
            indicators["vl"] = indicators["vl"] * 5

        self._line(ax, positions, indicators, "rsi9", "RSI9", "b")
        self._line(ax, positions, indicators, "rsi14", "RSI14", "k")
        if complexity >= 3:
            for column in ("roc10", "roc25"):
                if column in indicators.columns:
                    indicators[column] = indicators[column] + 50
            self._line(ax, positions, indicators, "roc10", "ROC10", "g")
            self._line(ax, positions, indicators, "roc25", "ROC25", "r")
        if complexity >= 2:
            self._line(ax, positions, indicators, "mfi14", "MFI", "#DD88DD")
            self._line(ax, positions, indicators, "ultosc", "UO", "m")
            self._line(ax, positions, indicators, "slowk", "SLOWK", "y")
            self._line(ax, positions, indicators, "slowd", "SLOWD", "#888888")
        if complexity >= 3:
            if "willr14" in indicators.columns:
                indicators["willr14"] = indicators["willr14"] + 100
            self._line(ax, positions, indicators, "willr14", "%R", "#BBBBFF")
        self._line(ax, positions, indicators, "vl", "VL", "c")

        volume = self._series(indicators, "v_rate")
        if volume is not None:
            ax.fill_between(positions, 0, volume, label="VOLUME", color="#DDFFFF")

        ax.set_yticks(list(OSCILLATOR_TICKS))
        ax.grid(True)

    def caption(
        self,
        stock: pd.DataFrame,
        classified: int,
        predicted: int,
        today: date | None = None,
    ) -> str:
        """
        Build the caption printed under the chart.

        Public because it is asserted by test: the caption is the only
        part of the image whose content this repository can check
        without comparing pixels.
        """
        if len(stock) < 2:
            raise DataFormatError(
                "Cannot caption {0}: at least two rows are needed".format(self.code)
            )
        volume = int(stock.iloc[-1]["Volume"])
        close = int(stock.iloc[-1]["Adj Close"])
        previous_close = int(stock.iloc[-2]["Adj Close"])
        highest = int(stock["High"].max())
        lowest = int(stock["Low"].min())

        change = close - previous_close
        # The same one-plus-change ratio the summaries report. See
        # finance.aggregation.change_ratio for why it is kept.
        ratio = round((1 + change) / close * 100, 2)
        change_text = "+{0}".format(change) if change >= 0 else str(change)
        trend = "↑" if classified else "↓"
        stamp = (today or datetime.today().date()).strftime("%Y/%m/%d")

        return (
            "{name}({code})  {today}\n"
            "終値:{close:,d} ({change}, {ratio}%)\n"
            " 出来高:{volume:,d} 最高:{highest:,d} 最安:{lowest:,d}"
            " 分類器予測:{trend} 回帰分析:{predicted:,d}".format(
                name=self.name,
                code=self.code,
                today=stamp,
                close=close,
                change=change_text,
                ratio=ratio,
                volume=volume,
                highest=highest,
                lowest=lowest,
                trend=trend,
                predicted=int(predicted),
            )
        )

    def _set_caption(
        self,
        ax,
        stock: pd.DataFrame,
        classified: int,
        predicted: int,
        today: date | None,
    ) -> None:
        """ Print the caption under the given axes. """
        text = self.caption(stock, classified, predicted, today)
        if self.font_properties is None:
            ax.set_xlabel(text)
            return
        ax.set_xlabel(text, fontproperties=self.font_properties)
