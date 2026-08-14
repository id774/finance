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
#  the HTTP client is caught at the boundary of the layer that owns it
#  and re-raised as one of these, so that no third-party exception type
#  reaches an entry point.
#
#  The data source errors are split further than the rest because the
#  operator's response differs by kind. A rejected API key needs a
#  configuration change; a rate limit needs a slower schedule; a dataset
#  the subscribed plan does not carry needs neither, and is not a fault
#  to be fixed. Collapsing them into one type would leave the nightly
#  log unable to say which of the three happened.
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
#  v1.1 2026-08-14
#       Add the authentication, rate limit, unavailable dataset and
#       invalid code errors the J-Quants adapter distinguishes.
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################


class FinanceError(Exception):
    """ Base of every error raised by this package. """


class ConfigurationError(FinanceError):
    """ Raised when a setting is missing or cannot be used as given. """


class DataSourceError(FinanceError):
    """ Raised when prices cannot be retrieved from the external source. """


class AuthenticationError(DataSourceError):
    """ Raised when the market data API rejects or is given no credential. """


class RateLimitError(DataSourceError):
    """ Raised when the market data API refuses a request as too frequent. """


class DataUnavailableError(DataSourceError):
    """
    Raised when the API is reachable but the data is outside the plan.

    This is not a fault. A subscription that does not carry a dataset,
    or a date outside the window the plan publishes, answers with this
    so that a caller can skip the stock and continue rather than treat
    the run as broken.
    """


class InvalidStockCodeError(DataSourceError):
    """ Raised when a stock code cannot name a listing at the source. """


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
