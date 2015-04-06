import sys
import os
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from ti import TechnicalIndicators
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

def test_get_sma():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    sma = ti.get_sma()
    sma = ti.get_sma(timeperiod=25)
    sma = ti.get_sma(timeperiod=75)

    expected = [19453.,
                18791.,
                17902.]
    result = (sma.ix['2015-03-20', 'sma5'],
              sma.ix['2015-03-20', 'sma25'],
              sma.ix['2015-03-20', 'sma75'])
    result = [round(x, 0) for x in result]
    eq_(expected, result)
    return sma

def test_get_ewma():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    ewma = ti.get_ewma()
    ewma = ti.get_ewma(span=25)
    ewma = ti.get_ewma(span=75)

    expected = [19429.,
                18821.,
                17991.]
    result = (ewma.ix['2015-03-20', 'ewma5'],
              ewma.ix['2015-03-20', 'ewma25'],
              ewma.ix['2015-03-20', 'ewma75'])
    result = [round(x, 0) for x in result]
    eq_(expected, result)
    result = [round(x, 0) for x in result]
    return ewma

def test_get_rsi():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    rsi = ti.get_rsi(timeperiod=14)

    expected = 74.98
    result = rsi.ix['2015-03-20', 'rsi14']
    result = round(result, 2)
    eq_(expected, result)
    return rsi

def test_get_roc():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    roc = ti.get_roc()

    expected = 3.11
    result = roc.ix['2015-03-20', 'roc']
    result = round(result, 2)
    eq_(expected, result)
    return roc

def test_get_macd():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    macd = ti.get_macd()

    expected = [383.,
                346.,
                37.]
    result = (macd.ix['2015-03-20', 'macd'],
              macd.ix['2015-03-20', 'macdsignal'],
              macd.ix['2015-03-20', 'macdhist'])
    result = [round(x, 0) for x in result]
    eq_(expected, result)
    return macd

def test_get_momentum():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    mom = ti.get_momentum(timeperiod=10)

    expected = 589.22
    result = mom.ix['2015-03-20', 'mom10']
    result = round(result, 2)
    eq_(expected, result)
    return mom

def test_get_bbands():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    bbands = ti.get_bbands()

    expected = [19661.0,
                19436.0,
                19210.0]
    result = (bbands.ix['2015-03-20', 'upperband'],
              bbands.ix['2015-03-20', 'middleband'],
              bbands.ix['2015-03-20', 'lowerband'])
    result = [round(x, 0) for x in result]
    eq_(expected, result)
    return bbands

def test_get_ret_index():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    ret_index = ti.get_ret_index()

    expected = 1.36
    result = ret_index.ix['2015-03-20', 'ret_index']
    result = round(result, 2)
    eq_(expected, result)
    return ret_index

if __name__ == '__main__':
    stock = testdata()
    sma = test_get_sma()
    ewma = test_get_ewma()
    rsi = test_get_rsi()
    macd = test_get_macd()
    momentum = test_get_momentum()
    bbands = test_get_bbands()
    ret_index = test_get_ret_index()
    stock = pd.merge(stock, sma,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, ewma,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, rsi,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, macd,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, momentum,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, bbands,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, ret_index,
                     left_index=True, right_index=True)
    print(stock.tail(10))
