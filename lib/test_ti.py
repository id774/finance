from nose.tools import *
from ti import *
import os
import pandas as pd

def testdata():
    days = 30
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    return stock_tse.asfreq('B')[days:]

def test_get_prices():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    prices = ti.get_prices()

    expected = 19560.22
    result = prices.ix['2015-03-20', 'prices']
    eq_(expected, result)
    return prices

def test_get_macd():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    macd = ti.get_macd()

    expected = (382.99041705210402,
                345.64437737584518,
                37.34603967625884)
    result = (macd.ix['2015-03-20', 'macd'],
              macd.ix['2015-03-20', 'macdsignal'],
              macd.ix['2015-03-20', 'macdhist'])
    eq_(expected, result)
    return macd

if __name__ == '__main__':
    prices = test_get_prices()
    macd = test_get_macd()
    df = pd.merge(prices, macd,
                  left_index=True, right_index=True)
    print(df)
