#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/__init__.py: Package root of finance
#
#  Description:
#  Hold the package version and the one place where logging is
#  configured. This module imports nothing beyond the standard library,
#  so every other module can import it without pulling in pandas,
#  matplotlib or a network client.
#
#  Logging is set up here rather than in each entry point because the
#  three commands are driven by the same cron job and append to the
#  same log file. One format, decided once, is what keeps their output
#  readable when interleaved.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - Standard library only
#
#  Version History:
#  v1.0 2026-08-14
#       Quiet the HTTP client's own loggers along with the rest.
#       Restructure the repository as an installable package.
#
########################################################################

import logging

__version__ = "1.0.1"

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# Third-party loggers that report their own retries and HTTP traffic at
# INFO or DEBUG. They are held at WARNING so that a nightly log stays a
# record of the pipeline rather than of the transport under it, and so
# that no request line carrying an API key header can reach the log
# through a library this package does not control.
QUIET_LOGGERS = ("matplotlib", "urllib3", "requests")


def configure_logging(level: str = "INFO") -> None:
    """
    Configure the root logger for a command line run.

    Args:
        level: Name of a standard logging level. An unknown name falls
            back to INFO rather than failing the run, because a log
            setting is not worth losing a night's data over.
    """
    resolved = logging.getLevelName(str(level).upper())
    if not isinstance(resolved, int):
        resolved = logging.INFO
    logging.basicConfig(level=resolved, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    logging.addLevelName(logging.WARNING, "WARN")
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(max(resolved, logging.WARNING))
