#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/errors.py: Error hierarchy of finance
#
#  Description:
#  Represent every failure the pipeline is expected to meet. The point
#  of the hierarchy is that a caller can tell a stock that could not be
#  fetched from a stock whose stored CSV is malformed, and decide to
#  continue or to stop on that difference.
#
#  An exception raised by pandas, TA-Lib, scikit-learn, matplotlib or
#  the price client is caught at the boundary of the layer that owns it
#  and re-raised as one of these, so that no third-party exception type
#  reaches an entry point.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - Standard library only
#
#  Version History:
#  v2.0 2026-08-14
#       Initial release.
#
########################################################################


class FinanceError(Exception):
    """ Base of every error raised by this package. """


class ConfigurationError(FinanceError):
    """ Raised when a setting is missing or cannot be used as given. """


class DataSourceError(FinanceError):
    """ Raised when prices cannot be retrieved from the external source. """


class DataFormatError(FinanceError):
    """ Raised when data on disk or from the source is not shaped as expected. """


class IndicatorError(FinanceError):
    """ Raised when an indicator cannot be computed from the given series. """


class ModelError(FinanceError):
    """ Raised when a model cannot be trained, loaded or applied. """


class ModelNotTrainedError(ModelError):
    """ Raised when a prediction is requested before the model is fitted. """


class StorageError(FinanceError):
    """ Raised when a file cannot be read or written. """


class NotificationError(FinanceError):
    """ Raised when a report cannot be delivered. """
