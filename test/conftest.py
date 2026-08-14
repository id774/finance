#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# conftest.py: Shared fixtures for the finance test suite
#
#  Description:
#  Provide the price data every test works from and a settings object
#  pointing at a temporary directory, so that no test reads or writes
#  the real data directory and none of them reach the network.
#
#  The price fixture is test/stock_N225.csv, which has been in this
#  repository since it was written and is the series every expected
#  value in the suite was derived from. It is not regenerated.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, pytest
#
#  Version History:
#  v2.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from finance.config import MailSettings, Settings

FIXTURE_DIR = Path(__file__).parent
RAW_PRICES = FIXTURE_DIR / "stock_N225.csv"
INDICATOR_FIXTURE = FIXTURE_DIR / "ti_N225.csv"

# The offset the legacy tests sliced the fixture at before computing.
# Kept so that the expected values carried over from them still line up
# with the windows they were computed on.
SHORT_OFFSET = 30
LONG_OFFSET = 91


@pytest.fixture(scope="session")
def raw_prices() -> pd.DataFrame:
    """ Return the full committed price fixture. """
    return pd.read_csv(RAW_PRICES, index_col=0, parse_dates=True)


@pytest.fixture(scope="session")
def indicator_fixture() -> pd.DataFrame:
    """ Return the committed indicator fixture the contract is checked against. """
    return pd.read_csv(INDICATOR_FIXTURE, index_col=0, parse_dates=True)


@pytest.fixture()
def prices(raw_prices: pd.DataFrame) -> pd.DataFrame:
    """ Return the window the indicator expectations were computed on. """
    return raw_prices.asfreq("B")[SHORT_OFFSET:]


@pytest.fixture()
def long_prices(raw_prices: pd.DataFrame) -> pd.DataFrame:
    """ Return the window the model expectations were computed on. """
    return raw_prices.asfreq("B")[LONG_OFFSET:]


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """ Return an empty temporary data directory. """
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


@pytest.fixture()
def settings(tmp_path: Path, data_dir: Path) -> Settings:
    """ Return settings bound to temporary directories, with mail disabled. """
    return Settings(
        data_dir=data_dir,
        history_dir=data_dir / "history",
        model_dir=tmp_path / "clf",
        stock_list="stocks.txt",
        start_date="2014-10-01",
        font_path="",
        log_level="INFO",
        mail=MailSettings(),
    )


@pytest.fixture()
def today() -> date:
    """ Return a fixed run date, one business day after the fixture ends. """
    return date(2015, 3, 23)


class StubSource:
    """
    A price source that answers from a frame instead of the network.

    Every test that needs prices uses this. Nothing in the default suite
    constructs the real Yahoo source, so a run without connectivity
    behaves the same as one with it.
    """

    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        self.frame = frame if frame is not None else pd.DataFrame()
        self.calls: list[tuple[str, date, date]] = []

    def fetch(self, code: str, start: date, end: date) -> pd.DataFrame:
        """ Record the request and return the configured frame. """
        self.calls.append((code, start, end))
        if self.frame.empty:
            return self.frame
        window = self.frame.loc[str(start) : str(end)]
        return window.copy()


@pytest.fixture()
def stub_source() -> type[StubSource]:
    """ Return the stub source class for a test to instantiate. """
    return StubSource
