#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/indicators.py: Technical indicator computation
#
#  Description:
#  Compute the technical indicators of one stock from its OHLCV frame.
#  Every method appends its columns to an indicator frame indexed by the
#  same business days as the input and returns that frame, so that the
#  order in which the methods are called is the column order of the
#  generated ti_CODE.csv.
#
#  That order is part of the contract with finance-dashboard and is
#  pinned by a test, not by convention. build_indicator_frame() below is
#  the single definition of the sequence; a caller that wants the
#  contract calls it rather than replaying the methods by hand.
#
#  Nothing here reads or writes a file, and nothing reaches the network.
#  The formulas are the ones this repository has always used: the move
#  from TA-Lib 0.4 to 0.7 and from pandas 0.16 to 3.x is an API change
#  only, verified column by column against test/ti_N225.csv.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - NumPy, pandas, TA-Lib
#
#  Version History:
#  v1.0 2026-08-14
#       Port to modern NumPy, pandas and TA-Lib without changing a
#       formula.
#
########################################################################

from __future__ import annotations

import numpy as np
import pandas as pd
import talib as ta
from talib import MA_Type

from finance.errors import DataFormatError, IndicatorError

BUSINESS_DAY = "B"

OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume", "Adj Close")

# Windows the daily pipeline computes. Kept here rather than in the
# pipeline because they are what the generated columns are named after.
SMA_PERIODS = (5, 25, 50, 75, 200)
EWMA_SPANS = (5, 25, 50, 75, 200)
ROC_PERIODS = (10, 25, 50, 75, 150)
MOMENTUM_PERIODS = (10, 25)
RSI_PERIODS = (9, 14)

VOLATILITY_WINDOW = 250
VOLATILITY_MIN_PERIODS = 50


class TechnicalIndicators:
    """
    Compute technical indicators for one stock.

    The instance holds the source frame and the indicator frame it is
    building. Each calc_* method adds its columns and returns the whole
    indicator frame, which is what lets the pipeline hand one method's
    result straight to the chart renderer.
    """

    def __init__(self, stock: pd.DataFrame) -> None:
        """
        Args:
            stock: OHLCV frame indexed by date. It is reindexed to
                business days internally, matching what the pipeline has
                always done before computing anything.

        Raises:
            DataFormatError: A required column is missing or the frame
                carries no usable row.
        """
        missing = [column for column in OHLCV_COLUMNS if column not in stock.columns]
        if missing:
            raise DataFormatError("Missing columns in stock data: {0}".format(", ".join(missing)))
        if stock.empty:
            raise DataFormatError("Stock data is empty")

        self.stock_raw = stock
        business = stock.asfreq(BUSINESS_DAY)
        close_series = business["Adj Close"].dropna()
        if close_series.empty:
            raise DataFormatError("Stock data has no usable close price")

        self.stock = pd.DataFrame(index=pd.Index(close_series.index.values))
        self.open = self._to_nparray(business["Open"])
        self.high = self._to_nparray(business["High"])
        self.low = self._to_nparray(business["Low"])
        self.close = self._to_nparray(business["Adj Close"])
        self.volume = self._to_nparray(business["Volume"])

    @staticmethod
    def _to_nparray(series: pd.Series) -> np.ndarray:
        """ Return a float64 array of the non-missing values of a series. """
        return np.array(series.dropna(), dtype="f8")

    def _talib(self, name: str, call):
        """
        Run a TA-Lib call and report a failure as an IndicatorError.

        TA-Lib raises bare Exception subclasses of its own for a series
        shorter than the window it was asked for. Those are caught here
        so that no TA-Lib type escapes this module.
        """
        try:
            return call()
        except Exception as exc:  # noqa: BLE001 - TA-Lib raises unrelated builtin types
            raise IndicatorError("{0} could not be computed: {1}".format(name, exc)) from exc

    def calc_sma(self, timeperiod: int = 5) -> pd.DataFrame:
        """ Add the simple moving average of the adjusted close. """
        self.stock["sma{0}".format(timeperiod)] = self._talib(
            "SMA", lambda: ta.SMA(self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_ewma(self, span: int = 5) -> pd.DataFrame:
        """
        Add the exponentially weighted moving average of the adjusted close.

        The three keyword arguments reproduce the defaults of the
        pandas.stats.moments.ewma() this replaced. Series.ewm() does not
        default to the same min_periods in every call form, so they are
        stated rather than assumed.
        """
        self.stock["ewma{0}".format(span)] = (
            pd.Series(self.close).ewm(span=span, adjust=True, min_periods=0).mean().to_numpy()
        )
        return self.stock

    def calc_rsi(self, timeperiod: int = 14) -> pd.DataFrame:
        """ Add the relative strength index. """
        self.stock["rsi{0}".format(timeperiod)] = self._talib(
            "RSI", lambda: ta.RSI(self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_mfi(self, timeperiod: int = 14) -> pd.DataFrame:
        """ Add the money flow index. """
        self.stock["mfi{0}".format(timeperiod)] = self._talib(
            "MFI",
            lambda: ta.MFI(self.high, self.low, self.close, self.volume, timeperiod=timeperiod),
        )
        return self.stock

    def calc_roc(self, timeperiod: int = 10) -> pd.DataFrame:
        """ Add the rate of change. """
        self.stock["roc{0}".format(timeperiod)] = self._talib(
            "ROC", lambda: ta.ROC(self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_cci(self, timeperiod: int = 14) -> pd.DataFrame:
        """ Add the commodity channel index. """
        self.stock["cci{0}".format(timeperiod)] = self._talib(
            "CCI", lambda: ta.CCI(self.high, self.low, self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_ultosc(self) -> pd.DataFrame:
        """ Add the ultimate oscillator. """
        self.stock["ultosc"] = self._talib(
            "ULTOSC", lambda: ta.ULTOSC(self.high, self.low, self.close)
        )
        return self.stock

    def calc_stoch(
        self,
        fastk_period: int = 5,
        slowk_period: int = 3,
        slowk_matype: int = 0,
        slowd_period: int = 3,
        slowd_matype: int = 0,
    ) -> pd.DataFrame:
        """ Add the slow stochastic oscillator as slowk and slowd. """
        slowk, slowd = self._talib(
            "STOCH",
            lambda: ta.STOCH(
                self.high,
                self.low,
                self.close,
                fastk_period=fastk_period,
                slowk_period=slowk_period,
                slowk_matype=slowk_matype,
                slowd_period=slowd_period,
                slowd_matype=slowd_matype,
            ),
        )
        self.stock["slowk"] = slowk
        self.stock["slowd"] = slowd
        return self.stock

    def calc_stochf(
        self, fastk_period: int = 5, fastd_period: int = 3, fastd_matype: int = 0
    ) -> pd.DataFrame:
        """ Add the fast stochastic oscillator as fastk and fastd. """
        fastk, fastd = self._talib(
            "STOCHF",
            lambda: ta.STOCHF(
                self.high,
                self.low,
                self.close,
                fastk_period=fastk_period,
                fastd_period=fastd_period,
                fastd_matype=fastd_matype,
            ),
        )
        self.stock["fastk"] = fastk
        self.stock["fastd"] = fastd
        return self.stock

    def calc_macd(
        self, fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9
    ) -> pd.DataFrame:
        """ Add the MACD line, its signal and their histogram. """
        macd, macdsignal, macdhist = self._talib(
            "MACD",
            lambda: ta.MACD(
                self.close,
                fastperiod=fastperiod,
                slowperiod=slowperiod,
                signalperiod=signalperiod,
            ),
        )
        self.stock["macd"] = macd
        self.stock["macdsignal"] = macdsignal
        self.stock["macdhist"] = macdhist
        return self.stock

    def calc_momentum(self, timeperiod: int = 10) -> pd.DataFrame:
        """ Add the momentum of the adjusted close. """
        self.stock["mom{0}".format(timeperiod)] = self._talib(
            "MOM", lambda: ta.MOM(self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_bbands(self) -> pd.DataFrame:
        """
        Add the Bollinger bands.

        MA_Type.T3 rather than the TA-Lib default is deliberate and
        original to this repository: the bands drawn on the charts are
        T3-smoothed.
        """
        upperband, middleband, lowerband = self._talib(
            "BBANDS", lambda: ta.BBANDS(self.close, matype=MA_Type.T3)
        )
        self.stock["upperband"] = upperband
        self.stock["middleband"] = middleband
        self.stock["lowerband"] = lowerband
        return self.stock

    def calc_sar(self, acceleration: float = 0.02, maximum: float = 0.2) -> pd.DataFrame:
        """ Add the parabolic SAR. """
        self.stock["sar"] = self._talib(
            "SAR",
            lambda: ta.SAR(self.high, self.low, acceleration=acceleration, maximum=maximum),
        )
        return self.stock

    def calc_willr(self, timeperiod: int = 14) -> pd.DataFrame:
        """ Add the Williams %R. """
        self.stock["willr{0}".format(timeperiod)] = self._talib(
            "WILLR", lambda: ta.WILLR(self.high, self.low, self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_tr(self) -> pd.DataFrame:
        """
        Add the true range and the volatility ratio derived from it.

        vl expresses the true range as a percentage of the typical
        price, which is what the lower chart panel plots.
        """
        self.stock["tr"] = self._talib(
            "TRANGE", lambda: ta.TRANGE(self.high, self.low, self.close)
        )
        typical_price = (self.high + self.low + self.close) / 3
        self.stock["vl"] = self.stock["tr"] / typical_price * 100
        return self.stock

    def calc_atr(self, timeperiod: int = 14) -> pd.DataFrame:
        """ Add the average true range. """
        self.stock["atr"] = self._talib(
            "ATR", lambda: ta.ATR(self.high, self.low, self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_natr(self, timeperiod: int = 14) -> pd.DataFrame:
        """ Add the normalized average true range. """
        self.stock["natr"] = self._talib(
            "NATR", lambda: ta.NATR(self.high, self.low, self.close, timeperiod=timeperiod)
        )
        return self.stock

    def calc_ret_index(self) -> pd.DataFrame:
        """
        Add the cumulative return index, based at 1 on the first row.

        This is the series both models are trained on, so its base is
        fixed at 1 rather than left as the NaN that pct_change() gives
        the first row.
        """
        returns = pd.Series(self.close).pct_change()
        ret_index = (1 + returns).cumprod()
        ret_index.iloc[0] = 1
        self.stock["ret_index"] = ret_index.to_numpy()
        return self.stock

    def calc_vol(
        self,
        rets: pd.Series,
        timeperiod: int = VOLATILITY_WINDOW,
        min_periods: int = VOLATILITY_MIN_PERIODS,
    ) -> pd.DataFrame:
        """ Add the annualized rolling volatility of the return index. """
        self.stock["vol"] = rets.rolling(timeperiod, min_periods=min_periods).std() * np.sqrt(
            timeperiod
        )
        return self.stock

    def calc_volume_rate(self) -> pd.DataFrame:
        """
        Add the volume expressed relative to the maximum of the window.

        Two scalings are produced because the charts use them on
        different axes: v_rate is drawn on the 0-100 oscillator panel,
        and v_rate_p is projected onto the price panel so that volume
        can be read against the candles.
        """
        rate = self.volume / self.volume.max()
        lowest = self.low.min()
        highest = self.high.max()
        # v_rate is assigned before v_rate_p so that the two columns keep
        # the order ti_CODE.csv has always had, then rescaled in place.
        self.stock["v_rate"] = rate
        self.stock["v_rate_p"] = rate * ((highest - lowest) / 4) + lowest
        self.stock["v_rate"] = rate * 50
        return self.stock

    def calc_rolling_corr(self, reference: pd.Series, window: int = 5) -> pd.DataFrame:
        """
        Add the rolling correlation of the returns against a reference series.

        Not part of the daily pipeline; kept because it is a working
        indicator this repository has always offered for ad hoc use.
        """
        reference_returns = reference.pct_change()
        own_returns = self.stock_raw["Adj Close"].pct_change()
        self.stock["rolling_corr"] = own_returns.rolling(window).corr(reference_returns)
        return self.stock


def build_indicator_frame(stock: pd.DataFrame) -> TechnicalIndicators:
    """
    Compute every indicator the daily pipeline writes, in contract order.

    The call sequence below is the column order of ti_CODE.csv. Changing
    it changes a generated file that finance-dashboard reads, so it is
    defined once here and asserted by test/test_contract.py.

    Args:
        stock: OHLCV frame of one stock.

    Returns:
        The TechnicalIndicators instance, with .stock holding every
        indicator column.
    """
    indicators = TechnicalIndicators(stock)

    for period in SMA_PERIODS:
        indicators.calc_sma(timeperiod=period)
    for span in EWMA_SPANS:
        indicators.calc_ewma(span=span)
    indicators.calc_bbands()
    indicators.calc_sar()
    returns = indicators.calc_ret_index()
    indicators.calc_vol(returns["ret_index"])
    for period in RSI_PERIODS:
        indicators.calc_rsi(timeperiod=period)
    indicators.calc_mfi()
    for period in ROC_PERIODS:
        indicators.calc_roc(timeperiod=period)
    indicators.calc_cci()
    indicators.calc_ultosc()
    indicators.calc_stoch()
    indicators.calc_stochf()
    indicators.calc_macd()
    indicators.calc_willr()
    for period in MOMENTUM_PERIODS:
        indicators.calc_momentum(timeperiod=period)
    indicators.calc_tr()
    indicators.calc_atr()
    indicators.calc_natr()
    indicators.calc_volume_rate()
    return indicators
