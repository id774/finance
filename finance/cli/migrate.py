#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/cli/migrate.py: One-off data migration command
#
#  Description:
#  Retire the price and indicator files a previous deployment wrote,
#  moving them into a dated archive so that the next daily run rebuilds
#  them from the current data source.
#
#  It is run once, by hand, when the data source changes. It is not part
#  of run.sh and nothing calls it on a schedule: an operation that moves
#  the operator's stored history has no business happening at 18:10
#  without them.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      finance-migrate --dry-run
#      finance-migrate
#      finance-migrate -h | --help
#      finance-migrate -v | --version
#
#  Options:
#  - -n, --dry-run
#      List what would move and move nothing.
#  - --config PATH, --data-dir PATH, --log-level NAME
#      As for the other commands.
#
#  Exit Codes:
#  - 0: The migration finished, including when there was nothing to do.
#  - 1: A file could not be moved, or a setting is unusable.
#  - 2: The command line was rejected.
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - Standard library only
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

from finance.cli import (
    EXIT_SUCCESS,
    add_common_arguments,
    execute,
    resolve_settings,
    start_logging,
)
from finance.migration import archive_legacy_data

logger = logging.getLogger(__name__)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """ Parse the command line. """
    parser = argparse.ArgumentParser(
        prog="finance-migrate",
        description=(
            "Move stored price and indicator files into a dated archive so that the "
            "next run rebuilds them from the current data source."
        ),
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", dest="dry_run",
        help="list what would move and move nothing",
    )
    add_common_arguments(parser)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """ Run the command and return its exit code. """
    arguments = parse_arguments(argv)

    def body() -> int:
        settings = resolve_settings(arguments)
        start_logging(settings)

        result = archive_legacy_data(settings.data_dir, dry_run=bool(arguments.dry_run))
        if result.count == 0:
            sys.stderr.write("[INFO] Nothing to migrate in {0}\n".format(settings.data_dir))
            return EXIT_SUCCESS

        verb = "Would move" if result.dry_run else "Moved"
        sys.stderr.write(
            "[INFO] {0} {1} file(s) to {2}\n".format(verb, result.count, result.archive_dir)
        )
        if not result.dry_run:
            sys.stderr.write(
                "[INFO] The next run with -u will rebuild them from the data source.\n"
            )
        return EXIT_SUCCESS

    return execute(body)


def run() -> None:
    """ Console script entry point. """
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
