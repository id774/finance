#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/reporting.py: The summary pipeline
#
#  Description:
#  Turn the stored indicator files of a stock list into one summary
#  table, write it where finance-dashboard reads it, and optionally keep
#  a dated copy under the history directory.
#
#  The history copy is the operator's archive. Nothing reads it back:
#  it exists so that a figure reported months ago can be checked against
#  what was reported at the time, which is also why the ratio formula in
#  finance.aggregation is preserved rather than corrected.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas
#
#  Version History:
#  v1.1 2026-08-19
#       Preserve the last valid summary when no stock can be aggregated.
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from finance import storage
from finance.aggregation import DEFAULT_SORT_KEY, Aggregator
from finance.analysis import load_indicator_frames
from finance.config import Settings
from finance.errors import DataFormatError
from finance.stocklist import read_stock_list

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryRequest:
    """ What one summary is asked to produce. """

    output: str
    stock_list: str
    span: int = 1
    sortkey: str | None = DEFAULT_SORT_KEY
    ascending: bool = False
    screening_key: str | None = None
    history: bool = False


@dataclass
class SummaryResult:
    """ What one summary produced. """

    output_path: Path
    history_path: Path | None
    rows: int


def build_summary(
    settings: Settings, request: SummaryRequest, today: date | None = None
) -> SummaryResult:
    """
    Build one summary table and write it.

    Args:
        settings: Where the indicator files are read and the summary is
            written.
        request: Which stocks, which columns, which order.
        today: The date staleness and the history file name are based
            on. Injected for tests.

    Returns:
        Where the summary was written and how many stocks it covers.

    Raises:
        StorageError: The stock list or the output cannot be read or
            written.
        DataFormatError: The stock list is malformed, the sort key
            names a column the layout has not got, or no stock can be
            summarized.
    """
    when = today or date.today()
    list_path = settings.data_file(request.stock_list)
    entries = read_stock_list(list_path)
    frames = load_indicator_frames(settings, entries)
    logger.info("Aggregating %d of %d stocks from %s", len(frames), len(entries), list_path)

    # Staleness is measured against the newest date the plan publishes,
    # not against today. On a delayed plan the freshest possible row is
    # already weeks old, and comparing it with today would report every
    # stock as stale and write an empty summary every night.
    as_of = settings.jquants.latest_available(when)

    table = Aggregator(frames).summarize(
        span=request.span,
        sortkey=request.sortkey,
        ascending=request.ascending,
        screening_key=request.screening_key,
        as_of=as_of,
    )
    if table.empty:
        raise DataFormatError("No stock had data recent enough to summarize")

    output_path = settings.data_file(request.output)
    storage.write_summary_csv(table, output_path)

    history_path: Path | None = None
    if request.history:
        history_path = settings.history_file(storage.history_filename(request.output, when))
        storage.write_summary_csv(table, history_path)
        logger.info("Kept a dated copy at %s", history_path)

    logger.info("Wrote %d rows to %s", len(table), output_path)
    return SummaryResult(output_path=output_path, history_path=history_path, rows=len(table))
