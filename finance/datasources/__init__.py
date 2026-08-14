#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/datasources/__init__.py: Price source abstraction
#
#  Description:
#  Define what the pipeline needs from a price source and nothing more:
#  given a code and a date range, return an OHLCV frame in the canonical
#  shape. Everything peculiar to a particular provider lives in a module
#  under this package and does not leave it.
#
#  The protocol exists so that a test can supply prices without a
#  network, and so that replacing the provider is one file rather than a
#  change spread through the analysis code. No client library is
#  imported here; create_source() imports the one it builds.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release, replacing the direct pandas-datareader and HTML
#       scraping calls.
#
########################################################################

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd

from finance.errors import ConfigurationError

# The columns every source must return, in this order. It is the order
# stock_CODE.csv has always been written in, and finance-dashboard links
# that file for download.
CANONICAL_COLUMNS: tuple[str, ...] = ("Open", "High", "Low", "Close", "Volume", "Adj Close")

YAHOO = "yahoo"
AVAILABLE_SOURCES = (YAHOO,)


@runtime_checkable
class StockDataSource(Protocol):
    """ What the pipeline requires of a price source. """

    def fetch(self, code: str, start: date, end: date) -> pd.DataFrame:
        """
        Return the daily prices of one stock.

        Args:
            code: The stock code as it appears in the stock list, not a
                provider symbol.
            start: First date to include.
            end: Last date to include.

        Returns:
            A frame carrying exactly CANONICAL_COLUMNS, indexed by
            tz-naive dates at midnight, sorted ascending. An empty frame
            when the source has nothing for the range, which is a normal
            answer and not an error.

        Raises:
            DataSourceError: The source could not be reached or answered
                with something unusable.
        """
        ...  # pragma: no cover - protocol declaration


def create_source(name: str = YAHOO) -> StockDataSource:
    """
    Build the named price source.

    Raises:
        ConfigurationError: The name is not one of AVAILABLE_SOURCES.
    """
    if name == YAHOO:
        from finance.datasources.yahoo import YahooFinanceSource

        return YahooFinanceSource()
    raise ConfigurationError(
        "Unknown data source: {0}. Choose one of {1}".format(name, ", ".join(AVAILABLE_SOURCES))
    )
