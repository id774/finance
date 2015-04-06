import numpy as np
import pandas as pd
import talib as ta
from talib import MA_Type
from pandas.stats.moments import ewma

class TechnicalIndicators():

    def __init__(self, stock, **kwargs):
        ts = stock.asfreq('B')['Adj Close'].dropna()
        self.stock = pd.DataFrame(index=ts.index.values)
        self.open = self._to_nparray(stock.asfreq('B')['Open'])
        self.high = self._to_nparray(stock.asfreq('B')['High'])
        self.low = self._to_nparray(stock.asfreq('B')['Low'])
        self.close = self._to_nparray(stock.asfreq('B')['Adj Close'])
        self.volume = self._to_nparray(stock.asfreq('B')['Volume'])

    def _to_nparray(self, s):
        return np.array(s.dropna(), dtype='f8')

    def get_sma(self, timeperiod=5):
        column = 'sma' + str(timeperiod)
        self.stock[column] = ta.SMA(self.close,
                                    timeperiod=timeperiod)
        return self.stock

    def get_ewma(self, span=5):
        column = 'ewma' + str(span)
        self.stock[column] = ewma(self.close, span=span)
        return self.stock

    def get_rsi(self, timeperiod=14):
        column = 'rsi' + str(timeperiod)
        self.stock[column] = ta.RSI(self.close,
                                    timeperiod=timeperiod)
        return self.stock

    def get_roc(self):
        self.stock['roc'] = ta.ROC(self.close)
        return self.stock

    def get_macd(self):
        macd, macdsignal, macdhist = ta.MACD(
            self.close,
            fastperiod=12, slowperiod=26, signalperiod=9)
        self.stock['macd'] = macd
        self.stock['macdsignal'] = macdsignal
        self.stock['macdhist'] = macdhist
        return self.stock

    def get_momentum(self, timeperiod=10):
        column = 'mom' + str(timeperiod)
        self.stock[column] = ta.MOM(
            self.close, timeperiod=timeperiod)
        return self.stock

    def get_bbands(self):
        upperband, middleband, lowerband = ta.BBANDS(
            self.close, matype=MA_Type.T3)
        self.stock['upperband'] = upperband
        self.stock['middleband'] = middleband
        self.stock['lowerband'] = lowerband
        return self.stock

    def get_ret_index(self):
        returns = pd.Series(self.close).pct_change()
        ret_index = (1 + returns).cumprod()
        ret_index[0] = 1
        self.stock['ret_index'] = ret_index.values
        return self.stock
