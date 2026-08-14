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
#  change spread through the analysis code. No HTTP client is imported
#  here; create_source() imports the one it builds.
#
#  There is one source, and it is J-Quants. A second name is not
#  reserved for a provider that does not exist: an entry in this table
#  is a promise that the name works, and a stub that raises would be a
#  worse answer than the configuration error an unknown name already
#  gets.
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
#       Replace the Yahoo Finance source with J-Quants and take the
#       settings the source is built from.
#       Initial release, replacing the direct pandas-datareader and HTML
#       scraping calls.
#
########################################################################

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd

from finance.config import JQuantsSettings
from finance.errors import ConfigurationError

# The columns every source must return, in this order. It is the order
# stock_CODE.csv has always been written in, and finance-dashboard links
# that file for download.
CANONICAL_COLUMNS: tuple[str, ...] = ("Open", "High", "Low", "Close", "Volume", "Adj Close")

JQUANTS = "jquants"
AVAILABLE_SOURCES = (JQUANTS,)


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


def create_source(settings: JQuantsSettings, name: str = JQUANTS) -> StockDataSource:
    """
    Build the named price source.

    Raises:
        ConfigurationError: The name is not one of AVAILABLE_SOURCES.
        AuthenticationError: The source needs a credential that is not
            configured. It is raised while the source is built rather
            than on the first fetch, so that a misconfigured run stops
            before it opens a socket.
    """
    if name == JQUANTS:
        from finance.datasources.jquants import JQuantsSource

        return JQuantsSource(settings)
    raise ConfigurationError(
        "Unknown data source: {0}. Choose one of {1}".format(name, ", ".join(AVAILABLE_SOURCES))
    )


class LazySource:
    """
    A price source that is built the first time it is asked to fetch.

    Half the runs of the daily job draw their charts from stored files
    and fetch nothing: the long and short chart passes read what the
    updating pass already wrote. Those runs must not require an API key,
    and a workstation redrawing a chart from a CSV must not need one
    either.

    Deferring construction is what allows that while keeping the
    guarantee that matters: the credential is still checked before the
    first request rather than during it, because building the source is
    what checks it and building happens before the first fetch.
    """

    def __init__(self, settings: JQuantsSettings, name: str = JQUANTS) -> None:
        self.settings = settings
        self.name = name
        self._source: StockDataSource | None = None

    def fetch(self, code: str, start: date, end: date) -> pd.DataFrame:
        """ Build the source if it is not built yet, and fetch. """
        if self._source is None:
            self._source = create_source(self.settings, self.name)
        return self._source.fetch(code, start, end)
