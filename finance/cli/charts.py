#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/cli/charts.py: Chart and indicator generation command
#
#  Description:
#  Fetch prices, compute the technical indicators, apply the two models
#  and draw a chart, for one stock or for every stock in a list.
#
#  The options are the ones bin/charts.py has always accepted, with the
#  same letters and the same meanings, because run.sh and the operator's
#  crontab pass them. optparse was replaced by argparse; nothing else
#  about the interface moved.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      finance-charts -s stocks.txt -d 2014-10-01 -y 240 -u
#      finance-charts -c 7203 -n トヨタ -y 240
#      finance-charts -h | --help
#      finance-charts -v | --version
#
#  Options:
#  - -c, --code CODE
#      Analyse one stock by code. Ignored when -s is given.
#  - -n, --name NAME
#      Display name of that stock, used in the chart caption.
#  - -s, --stock FILE
#      Analyse every stock listed in a file. Resolved against the data
#      directory when it is not an absolute path.
#  - -r, --readfile FILE
#      Read stored prices from this CSV instead of the default
#      stock_CODE.csv. Single stock runs only.
#  - -u, --update
#      Fetch new prices, rewrite stock_CODE.csv and ti_CODE.csv, and
#      persist the retrained models. Without it the run draws a chart
#      from what is already stored and writes nothing else.
#  - -d, --date DATE
#      Earliest date to fetch for a stock with no stored history, as
#      YYYY-MM-DD. Overrides the configured start date.
#  - -y, --days N
#      How many trailing rows to analyse and chart. 0 means all. The
#      value also selects the chart: over 300 writes long_CODE.png, 60
#      or fewer writes short_CODE.png, anything between writes
#      chart_CODE.png.
#  - -a, --axis N
#      1 draws the price panel alone, 2 adds the oscillator panel.
#  - -p, --complexity N
#      1 to 3, how many series each panel carries.
#
#  Exit Codes:
#  - 0: Every requested stock was analysed.
#  - 1: The run failed, or at least one stock in a list run failed.
#  - 2: The command line was rejected.
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - See pyproject.toml
#
#  Version History:
#  v2.0 2026-08-14
#       Replace optparse, honour -u, and call the shared pipeline.
#
########################################################################

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import replace

from finance.analysis import (
    DEFAULT_AXIS,
    DEFAULT_COMPLEXITY,
    DEFAULT_DAYS,
    Analysis,
    AnalysisRequest,
    run_many,
)
from finance.cli import (
    EXIT_FAILURE,
    EXIT_SUCCESS,
    add_common_arguments,
    execute,
    resolve_settings,
    start_logging,
)
from finance.datasources import create_source
from finance.errors import ConfigurationError
from finance.stocklist import read_stock_list
from finance.storage import price_filename

logger = logging.getLogger(__name__)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """ Parse the command line. """
    parser = argparse.ArgumentParser(
        prog="finance-charts",
        description="Compute technical indicators and draw charts.",
    )
    parser.add_argument("-c", "--code", dest="code", help="stock code")
    parser.add_argument("-n", "--name", dest="name", help="stock name")
    parser.add_argument("-s", "--stock", dest="stocktxt", help="stock list file")
    parser.add_argument("-r", "--readfile", dest="csvfile", help="stored price CSV")
    parser.add_argument(
        "-u", "--update", action="store_true", dest="update", help="fetch and rewrite data"
    )
    parser.add_argument("-d", "--date", dest="startdate", help="start date as YYYY-MM-DD")
    parser.add_argument(
        "-y", "--days", dest="days", type=int, default=DEFAULT_DAYS, help="rows to analyse"
    )
    parser.add_argument(
        "-a", "--axis", dest="axis", type=int, default=DEFAULT_AXIS, choices=(1, 2),
        help="1 for the price panel alone, 2 to add the oscillator panel",
    )
    parser.add_argument(
        "-p", "--complexity", dest="complexity", type=int, default=DEFAULT_COMPLEXITY,
        choices=(1, 2, 3), help="how many series each panel carries",
    )
    add_common_arguments(parser)
    return parser.parse_args(argv)


def build_requests(arguments: argparse.Namespace, settings) -> list[AnalysisRequest]:
    """
    Turn the parsed command line into the runs it asks for.

    Raises:
        ConfigurationError: Neither a code nor a stock list was given.
        StorageError: The stock list cannot be read.
        DataFormatError: The stock list is malformed.
    """
    common = {
        "days": arguments.days,
        "update": bool(arguments.update),
        "axis": arguments.axis,
        "complexity": arguments.complexity,
    }

    if arguments.stocktxt:
        path = settings.data_file(arguments.stocktxt)
        entries = read_stock_list(path)
        return [
            AnalysisRequest(
                code=entry.code,
                name=entry.name,
                fullname=entry.fullname,
                csvfile=price_filename(entry.code),
                **common,
            )
            for entry in entries
        ]

    if not arguments.code:
        raise ConfigurationError("Give either a stock code with -c or a stock list with -s")

    return [
        AnalysisRequest(
            code=arguments.code,
            name=arguments.name or arguments.code,
            fullname=arguments.name or arguments.code,
            csvfile=arguments.csvfile,
            **common,
        )
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """ Run the command and return its exit code. """
    arguments = parse_arguments(argv)

    def body() -> int:
        settings = resolve_settings(arguments)
        if arguments.startdate:
            settings = replace(settings, start_date=arguments.startdate)
            # Validate before any fetch, so a typo fails at once.
            settings.start_date_as_date()
        start_logging(settings)

        requests = build_requests(arguments, settings)
        analysis = Analysis(settings, create_source())
        results, failures = run_many(analysis, requests)

        logger.info("Analysed %d stocks, %d failed", len(results), len(failures))
        if failures:
            for code, error in failures:
                sys.stderr.write("[ERROR] {0}: {1}\n".format(code, error))
            return EXIT_FAILURE
        if not results:
            sys.stderr.write("[ERROR] Nothing was analysed\n")
            return EXIT_FAILURE
        return EXIT_SUCCESS

    return execute(body)


def run() -> None:
    """ Console script entry point. """
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
