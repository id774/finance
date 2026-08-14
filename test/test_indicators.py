#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_indicators.py: Regression tests for the technical indicators
#
#  Description:
#  Assert the value of every indicator at one fixed date on the
#  committed price fixture.
#
#  The expected numbers are not new. Each one is carried over from the
#  test suite this repository has had since 2015, when they were
#  produced by pandas 0.16, NumPy 1.11 and TA-Lib 0.4.9. They are
#  asserted here unchanged, on NumPy 2, pandas 3 and TA-Lib 0.7, which
#  is what makes this file the evidence that the upgrade moved the API
#  and not the arithmetic.
#
#  Test Cases:
#  - Every calc_* method reproduces its historical value at 2015-03-20.
#  - The exponentially weighted average matches the removed
#    pandas.stats.moments.ewma at three spans.
#  - build_indicator_frame() produces the contract column order.
#  - A frame missing a required column, or with no rows, is refused.
#  - A series too short for a window yields missing values, which is how
#    the leading empty cells of ti_CODE.csv arise.
#  - A bad window parameter surfaces as IndicatorError, not as a TA-Lib
#    exception.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, pytest
#
#  Version History:
#  v1.0 2026-08-14
#       Ported from the nose suite without changing an expected value.
#
########################################################################

from __future__ import annotations

import pandas as pd
import pytest

from finance.errors import DataFormatError, IndicatorError
from finance.indicators import TechnicalIndicators, build_indicator_frame

# The last row of the committed fixture. Every expected value below is
# read at this date, as it was in the suite these came from.
LAST_DATE = "2015-03-20"


def value(frame: pd.DataFrame, column: str, digits: int = 2) -> float:
    """ Read one indicator value at the fixture's last date. """
    return round(float(frame.loc[LAST_DATE, column]), digits)


def test_simple_moving_average(prices):
    indicators = TechnicalIndicators(prices)
    indicators.calc_sma()
    indicators.calc_sma(timeperiod=25)
    frame = indicators.calc_sma(timeperiod=75)

    assert value(frame, "sma5", 0) == 19453.0
    assert value(frame, "sma25", 0) == 18791.0
    assert value(frame, "sma75", 0) == 17902.0


def test_exponentially_weighted_moving_average(prices):
    indicators = TechnicalIndicators(prices)
    indicators.calc_ewma()
    indicators.calc_ewma(span=25)
    frame = indicators.calc_ewma(span=75)

    assert value(frame, "ewma5", 0) == 19429.0
    assert value(frame, "ewma25", 0) == 18821.0
    assert value(frame, "ewma75", 0) == 17991.0


def test_relative_strength_index(prices):
    frame = TechnicalIndicators(prices).calc_rsi(timeperiod=14)
    assert value(frame, "rsi14") == 74.98


def test_money_flow_index(prices):
    frame = TechnicalIndicators(prices).calc_mfi()
    assert value(frame, "mfi14") == 62.47


def test_rate_of_change(prices):
    frame = TechnicalIndicators(prices).calc_roc(timeperiod=10)
    assert value(frame, "roc10") == 3.11


def test_commodity_channel_index(prices):
    frame = TechnicalIndicators(prices).calc_cci()
    assert value(frame, "cci14") == 104.27


def test_ultimate_oscillator(prices):
    frame = TechnicalIndicators(prices).calc_ultosc()
    assert value(frame, "ultosc") == 72.56


def test_slow_stochastic(prices):
    frame = TechnicalIndicators(prices).calc_stoch()
    assert value(frame, "slowk") == 93.79
    assert value(frame, "slowd") == 93.32


def test_fast_stochastic(prices):
    frame = TechnicalIndicators(prices).calc_stochf()
    assert value(frame, "fastk") == 98.46
    assert value(frame, "fastd") == 93.79


def test_macd(prices):
    frame = TechnicalIndicators(prices).calc_macd()
    assert value(frame, "macd", 0) == 383.0
    assert value(frame, "macdsignal", 0) == 346.0
    assert value(frame, "macdhist", 0) == 37.0


def test_momentum(prices):
    frame = TechnicalIndicators(prices).calc_momentum(timeperiod=10)
    assert value(frame, "mom10") == 589.22


def test_bollinger_bands(prices):
    frame = TechnicalIndicators(prices).calc_bbands()
    assert value(frame, "upperband", 0) == 19661.0
    assert value(frame, "middleband", 0) == 19436.0
    assert value(frame, "lowerband", 0) == 19210.0


def test_parabolic_sar(prices):
    frame = TechnicalIndicators(prices).calc_sar()
    assert value(frame, "sar") == 18896.79


def test_williams_percent_r(prices):
    frame = TechnicalIndicators(prices).calc_willr(timeperiod=14)
    assert value(frame, "willr14") == -0.53


def test_true_range_and_volatility_ratio(prices):
    frame = TechnicalIndicators(prices).calc_tr()
    assert value(frame, "tr") == 148.81
    assert value(frame, "vl") == 0.76


def test_average_true_range(prices):
    frame = TechnicalIndicators(prices).calc_atr()
    assert value(frame, "atr") == 208.40


def test_normalized_average_true_range(prices):
    frame = TechnicalIndicators(prices).calc_natr()
    assert value(frame, "natr") == 1.07


def test_return_index(prices):
    frame = TechnicalIndicators(prices).calc_ret_index()
    assert value(frame, "ret_index") == 1.36
    # Based at exactly 1 on the first row, which is what both models
    # depend on when they scale a prediction back to a price.
    assert float(frame["ret_index"].iloc[0]) == 1.0


def test_volatility(prices):
    indicators = TechnicalIndicators(prices)
    returns = indicators.calc_ret_index()
    frame = indicators.calc_vol(returns["ret_index"])
    assert value(frame, "vol") == 1.56


def test_volume_rate(prices):
    frame = TechnicalIndicators(prices).calc_volume_rate()
    assert round(float(frame.loc["2015-03-19", "v_rate"]), 2) == 21.84


def test_rolling_correlation_against_itself_is_one(prices):
    indicators = TechnicalIndicators(prices)
    frame = indicators.calc_rolling_corr(prices["Adj Close"], window=5)
    correlation = frame["rolling_corr"].dropna()
    assert not correlation.empty
    assert round(float(correlation.iloc[-1]), 6) == 1.0


def test_build_indicator_frame_produces_the_contract_columns(prices, indicator_fixture):
    indicators = build_indicator_frame(prices)
    expected = [
        column
        for column in indicator_fixture.columns
        if column not in ("Open", "High", "Low", "Close", "Volume", "Adj Close")
        and column not in ("classified", "predicted")
    ]
    assert list(indicators.stock.columns) == expected


def test_missing_column_is_refused(prices):
    with pytest.raises(DataFormatError, match="Missing columns"):
        TechnicalIndicators(prices.drop(columns=["Volume"]))


def test_empty_frame_is_refused(prices):
    with pytest.raises(DataFormatError, match="empty"):
        TechnicalIndicators(prices.iloc[0:0])


def test_series_too_short_yields_missing_values(prices):
    # TA-Lib fills a window it cannot satisfy with NaN rather than
    # failing, which is the same reason the early rows of ti_CODE.csv
    # are empty. The pipeline relies on that, so it is asserted.
    short = prices.iloc[-3:]
    frame = TechnicalIndicators(short).calc_rsi(timeperiod=14)
    assert frame["rsi14"].isna().all()


def test_bad_parameter_is_reported_as_indicator_error(prices):
    with pytest.raises(IndicatorError, match="RSI"):
        TechnicalIndicators(prices).calc_rsi(timeperiod=-1)
