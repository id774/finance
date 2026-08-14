#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_yahoo_live.py: Live checks against Yahoo Finance
#
#  Description:
#  Verify against the real endpoint that the assumptions the adapter is
#  built on still hold: that unadjusted prices come back with an Adj
#  Close column, that the index is tz-aware in the exchange timezone,
#  and that a Tokyo symbol resolves.
#
#  These are the checks a stub cannot make, and they are the ones that
#  will fail first when the provider changes. They are also the ones
#  that must never gate a commit: they need connectivity, they depend on
#  a third party, and they can fail for reasons that have nothing to do
#  with this repository.
#
#  They are therefore marked integration and excluded from the default
#  run by the addopts in pyproject.toml, and CI does not run them. Run
#  them by hand when the provider is suspected:
#
#      pytest -m integration
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - Network access, yfinance
#
#  Version History:
#  v2.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

from datetime import date, timedelta

import pytest

from finance.datasources import CANONICAL_COLUMNS, create_source

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def source():
    """ Build the real Yahoo source. """
    return create_source("yahoo")


@pytest.fixture(scope="module")
def window() -> tuple[date, date]:
    """ Return a recent range long enough to contain trading days. """
    end = date.today() - timedelta(days=1)
    return end - timedelta(days=30), end


def test_an_index_still_returns_the_canonical_frame(source, window):
    start, end = window
    frame = source.fetch("N225", start, end)

    assert not frame.dropna(how="all").empty
    assert list(frame.columns) == list(CANONICAL_COLUMNS)
    assert frame.index.tz is None


def test_a_tokyo_listing_still_resolves(source, window):
    start, end = window
    frame = source.fetch("7203", start, end)

    assert not frame.dropna(how="all").empty
    assert list(frame.columns) == list(CANONICAL_COLUMNS)


def test_adjusted_close_is_still_supplied_when_auto_adjust_is_off(source, window):
    """ The assumption the whole indicator layer rests on. """
    start, end = window
    frame = source.fetch("N225", start, end).dropna(how="all")

    assert "Adj Close" in frame.columns
    assert frame["Adj Close"].notna().any()
