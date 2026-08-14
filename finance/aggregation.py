#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/aggregation.py: Summary table construction
#
#  Description:
#  Reduce the per stock indicator frames to the one-row-per-stock tables
#  that finance-dashboard renders and that the operator receives by
#  mail: the portfolio summary, the TOPIX Core30 summary and the RSI14
#  screening.
#
#  finance-dashboard reads these files positionally. It skips the header
#  line and zips the remaining fields against a fixed list of names, so
#  a column inserted, removed or reordered here does not fail there, it
#  silently shifts every later value into the wrong name. The two column
#  layouts are therefore stated as constants and asserted by
#  test/test_contract.py, and neither is derived from anything.
#
#  This module computes; it does not read or write. It is handed the
#  frames it aggregates.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas
#
#  Version History:
#  v1.0 2026-08-14
#       Replace the removed DataFrame.sort and .ix access, preserving
#       the values and the column order.
#
########################################################################

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from finance.errors import DataFormatError

# The two layouts finance-dashboard reads positionally. The trailing
# Name is what its templates link on, so it stays last in both.
TREND_COLUMNS: tuple[str, ...] = (
    "Open",
    "High",
    "Low",
    "Close",
    "Change",
    "Ratio",
    "Trend",
    "Pred",
    "Name",
)

SCREENING_COLUMNS: tuple[str, ...] = (
    "Open",
    "High",
    "Low",
    "Close",
    "Change",
    "Ratio",
    "__screening_key__",
    "Name",
)

# A stock whose newest indicator row is older than this is left out. It
# absorbs a run of market holidays without dropping the whole table, and
# it keeps a stock that stopped updating from being reported as current.
STALE_AFTER_DAYS = 10

DEFAULT_SORT_KEY = "Ratio"

logger = logging.getLogger(__name__)


def summary_columns(screening_key: str | None) -> tuple[str, ...]:
    """ Return the column layout of a summary, given its screening key. """
    if screening_key is None:
        return TREND_COLUMNS
    return tuple(screening_key if c == "__screening_key__" else c for c in SCREENING_COLUMNS)


def change_ratio(change: int, close: int) -> float:
    """
    Return the percentage figure the summaries and chart captions report.

    The formula divides one plus the change, not the change, by the
    close. That is not the textbook definition of a percentage change,
    but it is what this repository has reported since it was written,
    what the mailed summaries have always said and what the dashboard
    labels as the ratio. It is preserved deliberately; correcting it
    would restate every historical figure in data/history/.
    """
    return round((1 + change) / close * 100, 2)


class Aggregator:
    """ Build a summary table from the indicator frames of many stocks. """

    def __init__(self, frames: dict[tuple[str, str], pd.DataFrame]) -> None:
        """
        Args:
            frames: Indicator frames keyed by (code, name). Indices and
                stocks without a stored frame are expected to have been
                filtered out by the caller.
        """
        self.frames = frames

    def summarize(
        self,
        span: int = 1,
        sortkey: str | None = DEFAULT_SORT_KEY,
        ascending: bool = False,
        screening_key: str | None = None,
        as_of: date | None = None,
    ) -> pd.DataFrame:
        """
        Reduce every frame to one row and sort the result.

        Args:
            span: How many rows back the change is measured over. 1
                compares the last row with the one before it.
            sortkey: Column to sort by. None leaves the order alone.
            ascending: Sort direction.
            screening_key: An indicator column to report instead of the
                model outputs. Selects the nine column layout.
            as_of: The date staleness is measured against. It is the
                newest date the data source publishes, not the day the
                job runs: a source that is delayed by weeks would drop
                every stock as stale if it were compared with today.
                Defaults to the current date.

        Returns:
            A frame indexed by stock code, carrying the columns of
            summary_columns(screening_key). Empty when no stock is
            current enough to report.

        Raises:
            DataFormatError: sortkey names a column the layout has not
                got.
        """
        columns = summary_columns(screening_key)
        if sortkey is not None and sortkey not in columns:
            raise DataFormatError(
                "Cannot sort by {0}; this summary has {1}".format(sortkey, ", ".join(columns))
            )

        offset = span * -1 - 1
        cutoff = (as_of or date.today()) - timedelta(STALE_AFTER_DAYS)
        rows: dict[str, list[object]] = {}

        for (code, name), frame in self.frames.items():
            row = self._summarize_one(code, name, frame, offset, cutoff, screening_key)
            if row is not None:
                rows[code] = row

        if not rows:
            logger.warning("No stock had data recent enough to summarize")
            return pd.DataFrame([])

        # Built column-wise and transposed, which is what gives the
        # stock code the index position the Code header names.
        table = pd.DataFrame({code: pd.Series(values) for code, values in rows.items()})
        table.index = list(columns)
        result = table.T
        if sortkey is None:
            return result
        return result.sort_values(sortkey, ascending=ascending)

    def _summarize_one(
        self,
        code: str,
        name: str,
        frame: pd.DataFrame,
        offset: int,
        cutoff: date,
        screening_key: str | None,
    ) -> list[object] | None:
        """ Reduce one indicator frame to its summary row, or skip it. """
        if frame.empty:
            logger.warning("Skipping %s: no indicator rows", code)
            return None

        last_date = frame.index[-1].date()
        if last_date < cutoff:
            logger.info("Skipping %s: last row %s is older than %s", code, last_date, cutoff)
            return None

        if len(frame) < abs(offset):
            logger.warning(
                "Skipping %s: %d rows are not enough to measure a change over %d",
                code,
                len(frame),
                abs(offset) - 1,
            )
            return None

        try:
            start = int(frame.iloc[offset]["Adj Close"])
            end = int(frame.iloc[-1]["Adj Close"])
            open_price = int(frame.iloc[-1]["Open"])
            high = int(frame.iloc[-1]["High"])
            low = int(frame.iloc[-1]["Low"])
            close = int(frame.iloc[-1]["Adj Close"])
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping %s: price columns are unusable (%s)", code, exc)
            return None

        change = end - start
        ratio = change_ratio(change, close)
        head: list[object] = [open_price, high, low, close, change, ratio]

        if screening_key is not None:
            try:
                key_value = int(frame.iloc[-1][screening_key])
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Skipping %s: %s is unusable (%s)", code, screening_key, exc)
                return None
            return head + [key_value, name]

        try:
            trend = int(frame.iloc[-1]["classified"])
            predicted = int(frame.iloc[-1]["predicted"])
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping %s: model outputs are unusable (%s)", code, exc)
            return None
        return head + [trend, predicted, name]
