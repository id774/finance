#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/storage.py: File input and output
#
#  Description:
#  Centralize file I/O for the raw price CSV, technical indicator CSV,
#  summary tables, dated summary copies, data_source.txt and pickled
#  models.
#
#  File formats shared with finance-dashboard are described normatively
#  in doc/DATA_CONTRACT.md. This module keeps the matching separators,
#  index labels, data_source.txt file name and key order in constants so
#  call sites do not restate them.
#
#  This module decides no path. It is told where to write, so that the
#  layers above it own the layout and a test can point it at a temporary
#  directory.
#
#  The generated CSV and data_source.txt writers replace their target
#  atomically: content is completed in a sibling temporary file first, and
#  only a successful write is moved onto the target with os.replace(). A
#  failure -- while writing, while carrying over the existing target's
#  ownership and mode, or while replacing -- leaves the last good target
#  untouched and cleans up the temporary file. ModelStore.save() and the PNG
#  writer in finance/charts.py are outside this: models tolerate an unreadable
#  file by retraining, and chart regeneration always follows a successful CSV
#  write.
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
#  v1.1 2026-09-12
#       Atomically replace generated CSV/TXT output after complete writes.
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import logging
import os
import pickle
import stat
import uuid
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from finance.errors import DataFormatError, StorageError

# The contract with finance-dashboard, in one place.
PRICE_SEPARATOR = ","
PRICE_INDEX_LABEL = "Date"
SUMMARY_SEPARATOR = "\t"
SUMMARY_INDEX_LABEL = "Code"

PRICE_PREFIX = "stock_"
INDICATOR_PREFIX = "ti_"

# Where the generated data came from and how old it is, written so that
# the dashboard can say so rather than leaving a reader to assume the
# figures are live. Tab separated key and value, one pair per line, no
# header: it is read by a consumer that must not have to parse anything
# to display three facts.
DATA_SOURCE_FILE = "data_source.txt"
DATA_SOURCE_KEYS = ("source", "generated", "last_trading_day")

logger = logging.getLogger(__name__)


def price_filename(code: str) -> str:
    """ Return the file name of the raw price CSV of a stock. """
    return "{0}{1}.csv".format(PRICE_PREFIX, code)


def indicator_filename(code: str) -> str:
    """ Return the file name of the technical indicator CSV of a stock. """
    return "{0}{1}.csv".format(INDICATOR_PREFIX, code)


def history_filename(name: str, on: date) -> str:
    """
    Return the file name of a dated copy of a summary.

    The name keeps the double extension of the original scheme, as in
    summary.csv.20260814.csv, because the operator's archive is sorted
    and globbed on it.
    """
    return "{0}.{1}.csv".format(name, on.strftime("%Y%m%d"))


def ensure_directory(path: str | os.PathLike[str]) -> Path:
    """
    Create a directory if it is absent and return it.

    Raises:
        StorageError: The directory cannot be created.
    """
    target = Path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StorageError("Directory could not be created: {0}".format(target)) from exc
    return target


def _create_temp_file(target: Path) -> Path:
    """
    Create an empty, uniquely named sibling of target and return its path.

    Created with O_CREAT | O_EXCL at mode 0o666, the same request every
    regular file creation makes; the umask in effect, not a restrictive
    hardcoded mode, is what narrows it. A new file written this way and
    then moved onto an absent target keeps that mode, rather than the
    narrower default a general-purpose temp file helper would leave it at.
    """
    while True:
        candidate = target.with_name("{0}.{1}.tmp".format(target.name, uuid.uuid4().hex))
        try:
            fd = os.open(str(candidate), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        except FileExistsError:
            continue
        os.close(fd)
        return candidate


def _preserve_metadata(target: Path, temp_path: Path) -> None:
    """ Carry an existing target's mode, owner and group onto its replacement. """
    try:
        info = target.stat()
    except FileNotFoundError:
        return
    os.chmod(temp_path, stat.S_IMODE(info.st_mode))
    os.chown(temp_path, info.st_uid, info.st_gid)


def _discard_temp_file(temp_path: Path) -> None:
    """ Remove a temporary file left behind by a write that did not complete. """
    try:
        temp_path.unlink()
    except OSError:
        pass


def _replace_atomically(target: Path, write: Callable[[Path], None]) -> None:
    """
    Write target's replacement into a sibling temporary file, then move it
    into place with a single atomic os.replace().

    write is called with the temporary file's path and must write the
    complete content to it. Nothing about target is touched until the
    write, the metadata carry-over and the replace have all succeeded, so
    a failure at any point leaves the last good target exactly as it was.

    Raises:
        StorageError: The write, the metadata carry-over or the replace
            failed with an OSError.
    """
    ensure_directory(target.parent)
    temp_path = _create_temp_file(target)
    try:
        write(temp_path)
        _preserve_metadata(target, temp_path)
        os.replace(temp_path, target)
    except OSError as exc:
        _discard_temp_file(temp_path)
        raise StorageError("File could not be written: {0}".format(target)) from exc
    except BaseException:
        # An unexpected failure is not collapsed into StorageError, but the
        # temporary file is still cleaned up and target is still untouched.
        _discard_temp_file(temp_path)
        raise


def read_price_csv(path: str | os.PathLike[str]) -> pd.DataFrame:
    """
    Read a price or indicator CSV indexed by date.

    Raises:
        StorageError: The file does not exist or cannot be read.
        DataFormatError: The file cannot be parsed as a dated CSV.
    """
    target = Path(path)
    if not target.is_file():
        raise StorageError("File does not exist: {0}".format(target))
    try:
        frame = pd.read_csv(target, index_col=0, parse_dates=True)
    except OSError as exc:
        raise StorageError("File could not be read: {0}".format(target)) from exc
    except (ValueError, pd.errors.ParserError) as exc:
        raise DataFormatError("File is not a valid dated CSV: {0}".format(target)) from exc
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise DataFormatError("File is not indexed by date: {0}".format(target))
    return frame


def write_price_csv(frame: pd.DataFrame, path: str | os.PathLike[str]) -> None:
    """
    Write a price or indicator frame in the format the dashboard reads.

    An empty frame is not written. A file emptied by a failed run would
    read to the dashboard as a stock that has lost its history, which is
    worse than one that was not refreshed today.

    The write is atomic: a failure partway through leaves the existing
    file exactly as it was, rather than truncated or half rewritten.

    Raises:
        StorageError: The file cannot be written.
    """
    if frame.empty:
        logger.warning("Refusing to write an empty frame to %s", path)
        return
    target = Path(path)

    def write(temp_path: Path) -> None:
        frame.to_csv(temp_path, sep=PRICE_SEPARATOR, index_label=PRICE_INDEX_LABEL)

    _replace_atomically(target, write)
    logger.debug("Wrote %d rows to %s", len(frame), target)


def write_summary_csv(frame: pd.DataFrame, path: str | os.PathLike[str]) -> None:
    """
    Write a summary table in the tab separated format the dashboard reads.

    The write is atomic: a failure partway through leaves the existing
    file exactly as it was, rather than truncated or half rewritten.

    Raises:
        StorageError: The file cannot be written.
    """
    target = Path(path)

    def write(temp_path: Path) -> None:
        frame.to_csv(temp_path, sep=SUMMARY_SEPARATOR, index_label=SUMMARY_INDEX_LABEL)

    _replace_atomically(target, write)
    logger.debug("Wrote %d rows to %s", len(frame), target)


def read_summary_csv(path: str | os.PathLike[str]) -> pd.DataFrame:
    """
    Read back a summary table.

    Raises:
        StorageError: The file does not exist or cannot be read.
    """
    target = Path(path)
    if not target.is_file():
        raise StorageError("File does not exist: {0}".format(target))
    try:
        return pd.read_csv(target, sep=SUMMARY_SEPARATOR, index_col=0)
    except OSError as exc:
        raise StorageError("File could not be read: {0}".format(target)) from exc
    except (ValueError, pd.errors.ParserError) as exc:
        raise DataFormatError("File is not a valid summary CSV: {0}".format(target)) from exc


def read_text(path: str | os.PathLike[str]) -> str:
    """
    Read a generated file as text, for mailing it.

    Raises:
        StorageError: The file does not exist or cannot be read.
    """
    target = Path(path)
    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StorageError("File does not exist: {0}".format(target)) from exc
    except OSError as exc:
        raise StorageError("File could not be read: {0}".format(target)) from exc


def write_data_source(
    path: str | os.PathLike[str],
    source: str,
    generated: date,
    last_trading_day: date | None,
) -> None:
    """
    Record where the generated data came from and how old it is.

    Args:
        path: Where to write.
        source: Name of the provider and the plan, as one line.
        generated: The day the pipeline ran.
        last_trading_day: The newest trading day the data covers, or
            None when the run analysed nothing. An unknown date is
            written as an empty value rather than as today, because
            substituting the run date would make older or unknown data
            look more current than it is.

    The write is atomic: a failure partway through leaves the existing
    file exactly as it was, rather than truncated or half rewritten.

    Raises:
        StorageError: The file cannot be written.
    """
    values = {
        "source": source,
        "generated": generated.isoformat(),
        "last_trading_day": last_trading_day.isoformat() if last_trading_day else "",
    }
    lines = ["{0}\t{1}".format(key, values[key]) for key in DATA_SOURCE_KEYS]
    content = "\n".join(lines) + "\n"
    target = Path(path)

    def write(temp_path: Path) -> None:
        temp_path.write_text(content, encoding="utf-8")

    _replace_atomically(target, write)
    logger.debug("Wrote %s", target)


def merge_frames(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    """ Join a price frame and an indicator frame on their shared dates. """
    return pd.merge(left, right, left_index=True, right_index=True)


class ModelStore:
    """
    Load and save the pickled models of one directory.

    A model that cannot be unpickled is reported as absent rather than
    raised. Estimators pickled by an older scikit-learn do not load on a
    newer one, and refusing to run for that reason would stop the whole
    nightly job the first time the library is upgraded. Training a fresh
    model instead is exactly what happens for a stock seen for the first
    time.
    """

    def __init__(self, directory: str | os.PathLike[str]) -> None:
        self.directory = Path(directory)

    def path_for(self, name: str) -> Path:
        """ Return the path a named model is stored at. """
        return self.directory / name

    def load(self, name: str) -> Any | None:
        """ Return the stored model, or None when it is absent or unreadable. """
        target = self.path_for(name)
        if not target.is_file():
            return None
        try:
            with open(target, "rb") as handle:
                return pickle.load(handle)
        except (OSError, pickle.UnpicklingError, AttributeError, ImportError, EOFError) as exc:
            logger.warning(
                "Stored model %s could not be loaded (%s); training a new one", target, exc
            )
            return None

    def save(self, name: str, model: Any) -> None:
        """
        Store a model.

        Raises:
            StorageError: The model cannot be written.
        """
        ensure_directory(self.directory)
        target = self.path_for(name)
        try:
            with open(target, "wb") as handle:
                pickle.dump(model, handle)
        except (OSError, pickle.PicklingError) as exc:
            raise StorageError("Model could not be written: {0}".format(target)) from exc
        logger.debug("Saved model to %s", target)
