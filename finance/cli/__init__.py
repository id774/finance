#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/cli/__init__.py: Shared command line helpers
#
#  Description:
#  Hold what the four commands have in common: the exit codes they
#  agree on, the options every one of them accepts, and the wrapper that
#  turns an expected failure into a message on standard error and a
#  status, rather than a traceback.
#
#  The commands are thin on purpose. They parse arguments, resolve
#  settings, call one function in the application layer and report what
#  happened. No analysis is written here, and none is duplicated between
#  a command and the batch scripts that drive it.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Exit Codes:
#  - 0: The command finished its work.
#  - 1: The command failed, or a stock in a list run failed.
#  - 2: The command line was rejected by argparse.
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - Standard library only
#
#  Version History:
#  v1.2 2026-09-12
#       Preserve explicit history paths under --data-dir; this fixes incompatible
#       path resolution from the prior implementation.
#  v1.1 2026-09-09
#       Validate command-line log levels with the shared configuration rule.
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from finance import __version__, configure_logging
from finance.config import Settings, load_settings, validate_log_level
from finance.errors import ConfigurationError, FinanceError

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2

logger = logging.getLogger(__name__)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """ Add the options every command accepts. """
    parser.add_argument(
        "--config", dest="config", help="path of the YAML configuration file", default=None
    )
    parser.add_argument(
        "--data-dir", dest="data_dir", help="directory holding the generated files", default=None
    )
    parser.add_argument(
        "--log-level", dest="log_level", help="logging level name", default=None
    )
    parser.add_argument(
        "-v", "--version", action="version", version="finance {0}".format(__version__)
    )


def resolve_settings(arguments: argparse.Namespace) -> Settings:
    """
    Build settings, letting the command line override the environment.

    Raises:
        ConfigurationError: A setting is present but cannot be used.
    """
    settings = load_settings(arguments.config)
    overrides: dict[str, object] = {}
    if getattr(arguments, "data_dir", None):
        data_dir = Path(arguments.data_dir).expanduser().resolve()
        overrides["data_dir"] = data_dir
        # The history directory follows the data directory unless it was
        # configured on its own, so that --data-dir moves the whole
        # output of a run rather than half of it. Provenance, not value
        # equality, decides this: an explicit history directory that
        # happens to equal the derived default must still stay fixed.
        if not settings._history_dir_explicit:
            overrides["history_dir"] = data_dir / "history"
    if getattr(arguments, "log_level", None):
        overrides["log_level"] = validate_log_level(arguments.log_level)
    if not overrides:
        return settings
    return replace(settings, **overrides)


def execute(action: Callable[[], int]) -> int:
    """
    Run a command body, reporting an expected failure rather than raising.

    Args:
        action: The body of the command, returning an exit code.

    Returns:
        The exit code of the body, or EXIT_FAILURE when it raised a
        FinanceError.
    """
    try:
        return action()
    except ConfigurationError as exc:
        sys.stderr.write("[ERROR] Configuration: {0}\n".format(exc))
        return EXIT_FAILURE
    except FinanceError as exc:
        sys.stderr.write("[ERROR] {0}\n".format(exc))
        return EXIT_FAILURE
    except KeyboardInterrupt:
        sys.stderr.write("[WARN] Interrupted\n")
        return EXIT_FAILURE


def start_logging(settings: Settings) -> None:
    """ Configure logging from the resolved settings. """
    configure_logging(settings.log_level)
