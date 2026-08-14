#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/cli/notify.py: Report delivery command
#
#  Description:
#  Mail a generated summary to the operator. This replaces the Ruby
#  bin/email.rb invoked twice by run.sh, and takes its two positional
#  arguments in the same order, so the batch script reads the same.
#
#  The command exits successfully when mail is not configured or when
#  the host is not permitted to send. That is deliberate: a workstation
#  running the pipeline for a look at a chart should not fail its run
#  over a mail it was never meant to send.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      finance-notify
#      finance-notify portfolio.csv "Summary Report of My Portfolio"
#      finance-notify -h | --help
#      finance-notify -v | --version
#
#  Options:
#  - file
#      Generated file to send, relative to the data directory. Defaults
#      to summary.csv.
#  - subject
#      Human readable report name placed in the subject line.
#  - --dry-run
#      Print the message that would be sent and send nothing.
#
#  Exit Codes:
#  - 0: The report was sent, or sending was declined by configuration.
#  - 1: The report could not be read or could not be delivered.
#  - 2: The command line was rejected.
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - Standard library only
#
#  Version History:
#  v1.0 2026-08-14
#       Replace bin/email.rb.
#
########################################################################

from __future__ import annotations

import argparse
import logging
import socket
import sys
from collections.abc import Sequence

from finance.cli import (
    EXIT_SUCCESS,
    add_common_arguments,
    execute,
    resolve_settings,
    start_logging,
)
from finance.notification import (
    DEFAULT_REPORT,
    DEFAULT_SUBJECT,
    build_message,
    send_report,
)

logger = logging.getLogger(__name__)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """ Parse the command line. """
    parser = argparse.ArgumentParser(
        prog="finance-notify", description="Mail a generated report to the operator."
    )
    parser.add_argument(
        "file", nargs="?", default=DEFAULT_REPORT, help="generated file to send"
    )
    parser.add_argument(
        "subject", nargs="?", default=DEFAULT_SUBJECT, help="report name for the subject"
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run", help="print the message, send nothing"
    )
    add_common_arguments(parser)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """ Run the command and return its exit code. """
    arguments = parse_arguments(argv)

    def body() -> int:
        settings = resolve_settings(arguments)
        start_logging(settings)

        if arguments.dry_run:
            message = build_message(
                settings, arguments.file, arguments.subject, socket.gethostname()
            )
            sys.stdout.write(str(message))
            return EXIT_SUCCESS

        sent = send_report(settings, arguments.file, arguments.subject)
        if not sent:
            logger.info("Report %s was not sent", arguments.file)
        return EXIT_SUCCESS

    return execute(body)


def run() -> None:
    """ Console script entry point. """
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
