#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/cli/summary.py: Summary generation command
#
#  Description:
#  Aggregate the stored ti_CODE.csv files of a stock list into one tab
#  separated summary table, and optionally keep a dated copy.
#
#  The options are the ones bin/summary.py has always accepted. run.sh
#  invokes this command six times with different combinations of them,
#  and each combination produces one of the files finance-dashboard
#  reads, so the letters and their meanings are fixed.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      finance-summary -o summary.csv -y -r 1 -k Ratio
#      finance-summary -o screening_rsi14.csv -r 1 -c rsi14 -a -k rsi14
#      finance-summary -h | --help
#      finance-summary -v | --version
#
#  Options:
#  - -s, --stock FILE
#      Stock list to aggregate. Defaults to the configured list,
#      stocks.txt. Resolved against the data directory.
#  - -o, --output FILE
#      Name of the summary written into the data directory. Defaults to
#      out.csv.
#  - -r, --range N
#      How many rows back the change is measured over. 1 compares the
#      last row with the one before it.
#  - -k, --sortkey KEY
#      Column to sort by. Defaults to Ratio.
#  - -a, --ascending
#      Sort ascending instead of descending.
#  - -c, --screening_key KEY
#      Report this indicator column in place of the two model outputs.
#      Selects the nine column layout the dashboard reads for the
#      screening and Core30 tables.
#  - -y, --history
#      Also write a dated copy under the history directory.
#
#  Exit Codes:
#  - 0: The summary was written.
#  - 1: The summary could not be produced.
#  - 2: The command line was rejected.
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - See pyproject.toml
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from finance.aggregation import DEFAULT_SORT_KEY
from finance.cli import (
    EXIT_SUCCESS,
    add_common_arguments,
    execute,
    resolve_settings,
    start_logging,
)
from finance.reporting import SummaryRequest, build_summary

DEFAULT_OUTPUT = "out.csv"

logger = logging.getLogger(__name__)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """ Parse the command line. """
    parser = argparse.ArgumentParser(
        prog="finance-summary",
        description="Aggregate technical indicator files into a summary table.",
    )
    parser.add_argument("-s", "--stock", dest="stocktxt", help="stock list file")
    parser.add_argument(
        "-o", "--output", dest="output", default=DEFAULT_OUTPUT, help="output file name"
    )
    parser.add_argument(
        "-r", "--range", dest="span", type=int, default=1, help="rows the change spans"
    )
    parser.add_argument(
        "-k", "--sortkey", dest="sortkey", default=DEFAULT_SORT_KEY, help="column to sort by"
    )
    parser.add_argument(
        "-a", "--ascending", action="store_true", dest="ascending", help="sort ascending"
    )
    parser.add_argument(
        "-c", "--screening_key", dest="screening_key", help="indicator column to report"
    )
    parser.add_argument(
        "-y", "--history", action="store_true", dest="history", help="keep a dated copy"
    )
    add_common_arguments(parser)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """ Run the command and return its exit code. """
    arguments = parse_arguments(argv)

    def body() -> int:
        settings = resolve_settings(arguments)
        start_logging(settings)

        request = SummaryRequest(
            output=arguments.output,
            stock_list=arguments.stocktxt or settings.stock_list,
            span=arguments.span,
            sortkey=arguments.sortkey,
            ascending=bool(arguments.ascending),
            screening_key=arguments.screening_key,
            history=bool(arguments.history),
        )
        result = build_summary(settings, request)
        logger.info("Summary of %d stocks written to %s", result.rows, result.output_path)
        return EXIT_SUCCESS

    return execute(body)


def run() -> None:
    """ Console script entry point. """
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
