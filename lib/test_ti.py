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

def test_get_sma():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    sma = ti.get_sma()
    sma = ti.get_sma(timeperiod=25)
    sma = ti.get_sma(timeperiod=75)

    expected = (19452.864000000001,
                18791.391599999999,
                17902.110666666667)
    result = (sma.ix['2015-03-20', 'sma5'],
              sma.ix['2015-03-20', 'sma25'],
              sma.ix['2015-03-20', 'sma75'])
    eq_(expected, result)
    return sma

def test_get_ewma():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    ewma = ti.get_ewma()
    ewma = ti.get_ewma(span=25)
    ewma = ti.get_ewma(span=75)

    expected = (19428.781669154043,
                18821.274391427934,
                17990.951309119995)
    result = (ewma.ix['2015-03-20', 'ewma5'],
              ewma.ix['2015-03-20', 'ewma25'],
              ewma.ix['2015-03-20', 'ewma75'])
    eq_(expected, result)
    return ewma

def test_get_rsi():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    rsi = ti.get_rsi()

    expected = 74.982651133316381
    result = rsi.ix['2015-03-20', 'rsi14']
    eq_(expected, result)
    return rsi

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

def test_get_bbands():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    bbands = ti.get_bbands()

    expected = (19116.12719129512,
                16560.231199999998,
                14004.335208704877)
    result = (bbands.ix['2015-03-20', 'boll_upper'],
              bbands.ix['2015-03-20', 'boll_middle'],
              bbands.ix['2015-03-20', 'boll_lower'])
    eq_(expected, result)
    return bbands

if __name__ == '__main__':
    prices = test_get_prices()
    sma = test_get_sma()
    ewma = test_get_ewma()
    rsi = test_get_rsi()
    macd = test_get_macd()
    bbands = test_get_bbands()
    df = pd.merge(prices, sma,
                  left_index=True, right_index=True)
    df = pd.merge(df, ewma,
                  left_index=True, right_index=True)
    df = pd.merge(df, rsi,
                  left_index=True, right_index=True)
    df = pd.merge(df, macd,
                  left_index=True, right_index=True)
    df = pd.merge(df, bbands,
                  left_index=True, right_index=True)
    print(df.tail(10))
