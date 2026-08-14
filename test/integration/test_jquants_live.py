#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_jquants_live.py: The J-Quants API, for real
#
#  Description:
#  Check that the live endpoint still answers in the shape the adapter
#  was written against. This is the only file in the repository that
#  makes a request, and it is excluded from the default run and from CI
#  by the integration marker.
#
#  It is excluded because a third party must not decide whether a commit
#  is green, and because CI has no API key and must never be given one.
#  Run it by hand when the provider is suspected:
#
#      JQUANTS_API_KEY=... pytest -m integration
#
#  Nothing it fetches is written anywhere. The rows are examined in
#  memory and discarded: a response from this API may not be committed
#  to this repository as a fixture, and a test that saved one would be
#  the way that rule got broken. The invented fixtures in
#  test/test_datasources.py are what the adapter is really tested
#  against.
#
#  The date range asked for is inside the Free plan's published window,
#  so that a Free subscription can run this as well as a paid one.
#
#  Test Cases:
#  - The endpoint answers and the response normalizes to the canonical
#    frame.
#  - The frame carries the six canonical columns and a usable index.
#  - A rejected key raises AuthenticationError rather than something
#    from the HTTP client.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pytest, requests, a J-Quants API key in JQUANTS_API_KEY
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release, replacing the Yahoo live check.
#
########################################################################

from __future__ import annotations

import os
from dataclasses import replace
from datetime import date, timedelta

import pytest

from finance.config import JQuantsSettings
from finance.datasources import CANONICAL_COLUMNS, create_source
from finance.errors import AuthenticationError

pytestmark = pytest.mark.integration

# A large, long-listed company, so that the range is certain to hold
# trading days on any plan.
CODE = "7203"


def live_settings() -> JQuantsSettings:
    """ Return settings from the environment, skipping without a key. """
    key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not key:
        pytest.skip("JQUANTS_API_KEY is not set")
    return JQuantsSettings(api_key=key)


def test_the_endpoint_answers_in_the_expected_shape():
    settings = live_settings()
    today = date.today()
    end = settings.latest_available(today)
    start = end - timedelta(days=30)

    frame = create_source(settings).fetch(CODE, start, end)

    assert list(frame.columns) == list(CANONICAL_COLUMNS)
    assert frame.index.tz is None
    rows = frame.dropna(how="all")
    assert not rows.empty, "the plan window should hold trading days"
    assert (rows["High"] >= rows["Low"]).all()


def test_a_rejected_key_is_an_authentication_error():
    settings = replace(live_settings(), api_key="definitely-not-a-valid-key")
    with pytest.raises(AuthenticationError):
        create_source(settings).fetch(CODE, date(2025, 1, 6), date(2025, 1, 10))
