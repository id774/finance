import numpy as np
import pandas as pd
import talib as ta
from talib import MA_Type
from pandas.stats.moments import ewma

class TechnicalIndicators():

    def __init__(self, stock, **kwargs):
        self.stock_raw = stock
        ts = stock.asfreq('B')['Adj Close'].dropna()
        self.stock = pd.DataFrame(index=ts.index.values)
        self.open = self._to_nparray(stock.asfreq('B')['Open'])
        self.high = self._to_nparray(stock.asfreq('B')['High'])
        self.low = self._to_nparray(stock.asfreq('B')['Low'])
        self.close = self._to_nparray(stock.asfreq('B')['Adj Close'])
        self.volume = self._to_nparray(stock.asfreq('B')['Volume'])

    def _to_nparray(self, s):
        return np.array(s.dropna(), dtype='f8')

    def calc_sma(self, timeperiod=5):
        column = 'sma' + str(timeperiod)
        self.stock[column] = ta.SMA(self.close,
                                    timeperiod=timeperiod)
        return self.stock

    def calc_ewma(self, span=5):
        column = 'ewma' + str(span)
        self.stock[column] = ewma(self.close, span=span)
        return self.stock

    def calc_rsi(self, timeperiod=14):
        column = 'rsi' + str(timeperiod)
        self.stock[column] = ta.RSI(self.close,
                                    timeperiod=timeperiod)
        return self.stock

    def calc_mfi(self, timeperiod=14):
        column = 'mfi' + str(timeperiod)
        self.stock[column] = ta.MFI(self.high,
                                    self.low,
                                    self.close,
                                    self.volume,
                                    timeperiod=timeperiod)
        return self.stock

    def calc_roc(self, timeperiod=10):
        column = 'roc' + str(timeperiod)
        self.stock[column] = ta.ROC(self.close,
                                    timeperiod=timeperiod)
        return self.stock

    def calc_cci(self, timeperiod=14):
        column = 'cci' + str(timeperiod)
        self.stock[column] = ta.CCI(self.high,
                                    self.low,
                                    self.close,
                                    timeperiod=timeperiod)
        return self.stock

    def calc_ultosc(self):
        self.stock['ultosc'] = ta.ULTOSC(self.high,
                                         self.low,
                                         self.close)
        return self.stock

    def calc_stoch(self,
                   fastk_period=5, slowk_period=3,
                   slowk_matype=0, slowd_period=3,
                   slowd_matype=0):
        stoch = ta.STOCH(self.high,
                         self.low,
                         self.close,
                         fastk_period=fastk_period,
                         slowk_period=slowk_period,
                         slowk_matype=slowk_matype,
                         slowd_period=slowd_period,
                         slowd_matype=slowd_matype)
        self.stock['slowk'] = stoch[0]
        self.stock['slowd'] = stoch[1]
        return self.stock

    def calc_stochf(self,
                    fastk_period=5, fastd_period=3,
                    fastd_matype=0):
        stochf = ta.STOCHF(self.high,
                           self.low,
                           self.close,
                           fastk_period=fastk_period,
                           fastd_period=fastd_period,
                           fastd_matype=fastd_matype)
        self.stock['fastk'] = stochf[0]
        self.stock['fastd'] = stochf[1]
        return self.stock

    def calc_macd(self,
                  fastperiod=12, slowperiod=26, signalperiod=9):
        macd, macdsignal, macdhist = ta.MACD(
            self.close,
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod)
        self.stock['macd'] = macd
        self.stock['macdsignal'] = macdsignal
        self.stock['macdhist'] = macdhist
        return self.stock

    def calc_momentum(self, timeperiod=10):
        column = 'mom' + str(timeperiod)
        self.stock[column] = ta.MOM(
            self.close, timeperiod=timeperiod)
        return self.stock

    def calc_bbands(self):
        upperband, middleband, lowerband = ta.BBANDS(
            self.close, matype=MA_Type.T3)
        self.stock['upperband'] = upperband
        self.stock['middleband'] = middleband
        self.stock['lowerband'] = lowerband
        return self.stock

    def calc_sar(self, acceleration=0.02, maximum=0.2):
        self.stock['sar'] = ta.SAR(self.high,
                                   self.low,
                                   acceleration=acceleration,
                                   maximum=maximum)
        return self.stock

    def calc_willr(self, timeperiod=14):
        column = 'willr' + str(timeperiod)
        self.stock[column] = ta.WILLR(self.high,
                                      self.low,
                                      self.close,
                                      timeperiod=timeperiod)
        return self.stock

    def calc_tr(self):
        self.stock['tr'] = ta.TRANGE(self.high,
                                     self.low,
                                     self.close)
        self.stock['vl'] = self.stock['tr'] / ((self.high +
                                                self.low +
                                                self.close) / 3) * 100
        return self.stock

    def calc_atr(self, timeperiod=14):
        self.stock['atr'] = ta.ATR(self.high,
                                   self.low,
                                   self.close,
                                   timeperiod=timeperiod)
        return self.stock

    def calc_natr(self, timeperiod=14):
        self.stock['natr'] = ta.NATR(self.high,
                                     self.low,
                                     self.close,
                                     timeperiod=timeperiod)
        return self.stock

    def calc_ret_index(self):
        returns = pd.Series(self.close).pct_change()
        ret_index = (1 + returns).cumprod()
        ret_index[0] = 1
        self.stock['ret_index'] = ret_index.values
        return self.stock

    def calc_vol(self, rets, timeperiod=250, min_periods=50):
        self.stock['vol'] = pd.rolling_std(
            rets,
            timeperiod,
            min_periods=min_periods) * np.sqrt(timeperiod)
        return self.stock

    def calc_volume_rate(self):
        self.stock['v_rate'] = (self.volume /
                                self.volume.max())
        _under = self.low.min()
        _top = self.high.max()
        _range = _top - _under
        self.stock['v_rate_p'] = (self.stock['v_rate'] *
                                  (_range / 4) + _under)
        self.stock['v_rate'] = self.stock['v_rate'] * 50
        return self.stock

    def calc_rolling_corr(self, reference, window=5):
        r = reference.pct_change()
        c = self.stock_raw['Adj Close'].pct_change()
        self.stock['rolling_corr'] = pd.rolling_corr(c, r, window)
        return self.stock
