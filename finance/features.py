#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/features.py: Training set construction
#
#  Description:
#  Turn a return index series into the training sets the two models use.
#  Both build sliding windows of fourteen consecutive values; they
#  differ in what they predict from one. binary_class() labels whether
#  the next value rises, and proportion_class() takes the next value
#  itself as the target.
#
#  The window boundaries are expressed as negative offsets from the end
#  of the series, which is how the models are kept anchored to the most
#  recent data: the last window a training set contains is always the
#  one immediately before the fourteen values a prediction will be made
#  from.
#
#  The legacy implementation reached these positions through the removed
#  DataFrame.ix and through Series.__getitem__ falling back to positional
#  lookup on a DatetimeIndex. Both are now explicit .iloc calls. The
#  arithmetic is unchanged and reproduces the original labels exactly.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - NumPy, pandas
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import numpy as np
import pandas as pd

from finance.errors import DataFormatError

WINDOW_SIZE = 14

# The training set never reaches further back than this many rows. The
# limit is original to this repository and bounds how long a nightly run
# spends fitting when a series has years of history behind it.
MAX_TRAINING_WINDOW = 135


def _bounded_start(window: int) -> int:
    """ Return the negative offset the training set starts at. """
    return min(window, MAX_TRAINING_WINDOW) * -1


def binary_class(
    arr: pd.Series, window: int = WINDOW_SIZE + 2
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the classification training set: does the next value rise?

    Args:
        arr: The return index series.
        window: How far back to reach, as a positive row count. Capped
            at MAX_TRAINING_WINDOW.

    Returns:
        A tuple of the feature windows and their 0/1 labels.

    Raises:
        DataFormatError: The series is too short to yield a window.
    """
    start = _bounded_start(window)
    _require_length(arr, start)
    features: list[np.ndarray] = []
    labels: list[int] = []
    for offset in np.arange(start, -(WINDOW_SIZE + 1)):
        end = offset + WINDOW_SIZE
        feature = arr.iloc[offset:end]
        labels.append(1 if feature.iloc[-1] < arr.iloc[end] else 0)
        features.append(feature.to_numpy())
    return np.array(features), np.array(labels)


def proportion_class(
    arr: pd.Series, window: int = WINDOW_SIZE + 2
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build the regression training set: what is the next value?

    Args:
        arr: The return index series.
        window: How far back to reach, as a positive row count. Capped
            at MAX_TRAINING_WINDOW.

    Returns:
        A tuple of the feature windows and their continuous targets.

    Raises:
        DataFormatError: The series is too short to yield a window.
    """
    start = _bounded_start(window)
    _require_length(arr, start)
    features: list[np.ndarray] = []
    targets: list[float] = []
    for offset in np.arange(start, -WINDOW_SIZE):
        end = offset + WINDOW_SIZE
        features.append(arr.iloc[offset:end].to_numpy())
        targets.append(arr.iloc[end])
    return np.array(features), np.array(targets)


def _require_length(arr: pd.Series, start: int) -> None:
    """ Refuse a series that cannot supply the requested window. """
    if len(arr) < abs(start):
        raise DataFormatError(
            "Need at least {0} rows to build a training set, got {1}".format(abs(start), len(arr))
        )


def latest_window(arr: pd.Series) -> np.ndarray:
    """
    Return the most recent window, shaped as the single sample to predict from.

    Raises:
        DataFormatError: Fewer than WINDOW_SIZE rows are available.
    """
    if len(arr) < WINDOW_SIZE:
        raise DataFormatError(
            "Need at least {0} rows to predict, got {1}".format(WINDOW_SIZE, len(arr))
        )
    return arr.to_numpy()[-WINDOW_SIZE:].reshape([1, -1])
