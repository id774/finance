from nose.tools import *
import datetime
import pandas as pd
import pandas.io.data as web
from calc_rsi import calc_rsi

def test_calc_rsi():
    days = 30
    start = '2014-09-01'
    end = '2015-01-01'
    start = datetime.datetime.strptime(start, '%Y-%m-%d')
    stock_tse = web.DataReader('^N225', 'yahoo', start, end)
    stock_d = stock_tse.asfreq('B')[days:]
    rsi = calc_rsi(stock_d, n=14)
    result = rsi.ix['2014-10-30', 'Adj Close']
    expected = 55.935331193638028
    eq_(expected, result)
    return result

if __name__ == '__main__':
    print(test_calc_rsi())
