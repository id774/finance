#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/stocklist.py: Stock list parsing
#
#  Description:
#  Read the comma separated listings that decide which stocks a run
#  covers: stocks.txt, topix_core30.txt and the operator's private
#  holdings file. All three share one format and differ only in how many
#  columns they carry.
#
#  The first two columns, the code and the short name, are the ones
#  every file has and the only two finance-dashboard reads out of
#  stocks.txt. The rest are optional and are kept because the longer
#  name appears in a chart caption.
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
#       Replace the pandas based reader with a plain CSV reader.
#
########################################################################

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from finance.errors import DataFormatError, StorageError

# Codes that name a market index rather than a listed company. They are
# excluded from the summaries, because a change ratio against an index
# is not comparable with one against a share price, and they are fetched
# through a different symbol form.
INDEX_CODES = frozenset({"N225", "GSPC", "IXIC", "DJI"})

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StockEntry:
    """ One line of a stock list. """

    code: str
    name: str
    fullname: str = ""

    @property
    def is_index(self) -> bool:
        """ Report whether this entry names a market index. """
        return self.code in INDEX_CODES

    @property
    def display_name(self) -> str:
        """ Return the name used in a chart caption. """
        return self.fullname or self.name


def read_stock_list(path: str | os.PathLike[str]) -> list[StockEntry]:
    """
    Read a stock list file.

    Args:
        path: Path of a comma separated file whose first two columns are
            the code and the short name.

    Returns:
        The entries in file order. Blank lines are skipped.

    Raises:
        StorageError: The file does not exist or cannot be read.
        DataFormatError: A non-blank line carries fewer than two fields.
    """
    target = Path(path)
    try:
        with open(target, encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
    except FileNotFoundError as exc:
        raise StorageError("Stock list does not exist: {0}".format(target)) from exc
    except OSError as exc:
        raise StorageError("Stock list could not be read: {0}".format(target)) from exc

    entries: list[StockEntry] = []
    for number, fields in enumerate(rows, start=1):
        if not fields or not fields[0].strip():
            continue
        if len(fields) < 2:
            raise DataFormatError(
                "{0} line {1}: expected at least a code and a name".format(target, number)
            )
        entries.append(
            StockEntry(
                code=fields[0].strip(),
                name=fields[1].strip(),
                fullname=fields[2].strip() if len(fields) > 2 else "",
            )
        )
    if not entries:
        raise DataFormatError("Stock list is empty: {0}".format(target))
    logger.debug("Read %d entries from %s", len(entries), target)
    return entries
