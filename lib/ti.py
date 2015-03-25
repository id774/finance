import numpy as np
import pandas as pd
import talib as ta
from pandas.stats.moments import ewma

class TechnicalIndicators():

    def __init__(self, stock, **kwargs):
        stock = stock.asfreq('B')['Adj Close'].dropna()
        self.prices = np.array(stock)
        self.analysis = pd.DataFrame(index=stock.index.values)

    def get_prices(self):
        self.analysis['prices'] = self.prices
        return self.analysis

    def get_sma(self, timeperiod=5):
        column = 'sma' + str(timeperiod)
        self.analysis[column] = ta.SMA(self.prices,
                                       timeperiod=timeperiod)
        return self.analysis

    def get_ewma(self, span=5):
        column = 'ewma' + str(span)
        self.analysis[column] = ewma(self.prices, span=span)
        return self.analysis

    def get_rsi(self, timeperiod=14):
        column = 'rsi' + str(timeperiod)
        self.analysis[column] = ta.RSI(self.prices,
                                       timeperiod=timeperiod)
        return self.analysis

    def get_macd(self):
        macd, macdsignal, macdhist = ta.MACD(
            self.prices, fastperiod=12, slowperiod=26, signalperiod=9)
        self.analysis['macd'] = macd
        self.analysis['macdsignal'] = macdsignal
        self.analysis['macdhist'] = macdhist
        return self.analysis

    def get_bbands(self):
        boll_upper, boll_middle, boll_lower = ta.BBANDS(
            self.prices, timeperiod=200, nbdevup=2, nbdevdn=2, matype=0)
        self.analysis['boll_upper'] = boll_upper
        self.analysis['boll_middle'] = boll_middle
        self.analysis['boll_lower'] = boll_lower
        return self.analysis
