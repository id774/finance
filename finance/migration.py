#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/migration.py: Retiring data written before the source changed
#
#  Description:
#  Move the price and indicator files a previous deployment produced out
#  of the data directory, so that the next run rebuilds them from the
#  current data source instead of appending to them.
#
#  Why this exists at all: the stored price files were written when
#  prices came from Yahoo Finance, where the four OHLC columns were as
#  traded and Adj Close alone was adjusted. The current source is
#  J-Quants, where all six columns are on one basis, adjusted for share
#  splits. The two are not the same series. The daily job merges stored
#  rows with newly fetched ones, and merging these two would produce a
#  file whose older half and newer half mean different things -- a
#  difference no indicator would report and no chart would show.
#
#  So the daily job does not attempt it. This is a separate command, run
#  once by hand, and the data source knows nothing about it: no part of
#  finance/datasources looks at what is on disk or at where it came
#  from. Retiring old data is an operator's decision about an operator's
#  files, and it stays that.
#
#  Nothing is deleted. The files are moved into a dated directory beside
#  the data, which keeps the operator's own history intact and leaves
#  them free to look at what was there. Removing that directory is
#  another decision, and also theirs.
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
#       Initial release.
#
########################################################################

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from finance import storage
from finance.errors import StorageError

# The prefix the retired files are moved under, inside the data
# directory, with the date of the migration appended.
ARCHIVE_PREFIX = "legacy"

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """ What a migration moved, or would move. """

    archive_dir: Path
    moved: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def count(self) -> int:
        """ Return how many files were moved. """
        return len(self.moved)


def legacy_files(data_dir: Path) -> list[Path]:
    """
    Return the generated price and indicator files of a data directory.

    Only the two per-stock series are listed. The summaries and the
    charts are rewritten wholesale by the next run and carry nothing
    forward, so they need no migration; the stock lists are input and
    are not touched.
    """
    if not data_dir.is_dir():
        return []
    prefixes = (storage.PRICE_PREFIX, storage.INDICATOR_PREFIX)
    found = [
        path
        for path in sorted(data_dir.glob("*.csv"))
        if path.is_file() and path.name.startswith(prefixes)
    ]
    return found


def archive_legacy_data(
    data_dir: Path, on: date | None = None, dry_run: bool = False
) -> MigrationResult:
    """
    Move the stored price and indicator files into a dated archive.

    Args:
        data_dir: The directory the pipeline generates into.
        on: The date naming the archive directory. Defaults to today.
        dry_run: Report what would move without moving it.

    Returns:
        Where the files went and which ones they were.

    Raises:
        StorageError: A file could not be moved.
    """
    when = on or date.today()
    archive_dir = data_dir / "{0}.{1}".format(ARCHIVE_PREFIX, when.strftime("%Y%m%d"))
    files = legacy_files(data_dir)
    result = MigrationResult(archive_dir=archive_dir, dry_run=dry_run)

    if not files:
        logger.info("No stored price or indicator files in %s", data_dir)
        return result

    if dry_run:
        result.moved = [path.name for path in files]
        logger.info("Would move %d file(s) to %s", len(files), archive_dir)
        return result

    storage.ensure_directory(archive_dir)
    for path in files:
        try:
            shutil.move(str(path), str(archive_dir / path.name))
        except OSError as exc:
            raise StorageError(
                "File could not be moved to the archive: {0}".format(path)
            ) from exc
        result.moved.append(path.name)

    logger.info("Moved %d file(s) to %s", len(result.moved), archive_dir)
    return result
