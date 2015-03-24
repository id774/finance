import numpy as np
import pandas as pd
import talib as ta

class TechnicalIndicators():

    def __init__(self, stock, **kwargs):
        stock = stock.asfreq('B')['Adj Close'].dropna()
        self.prices = np.array(stock)
        self.analysis = pd.DataFrame(index=stock.index.values)

    def get_prices(self):
        self.analysis['prices'] = self.prices
        return self.analysis

    def get_macd(self):
        macd, macdsignal, macdhist = ta.MACD(
            self.prices, fastperiod=12, slowperiod=26, signalperiod=9)
        self.analysis['macd'] = macd
        self.analysis['macdsignal'] = macdsignal
        self.analysis['macdhist'] = macdhist
        return self.analysis
