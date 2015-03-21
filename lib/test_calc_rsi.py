from nose.tools import *
import os
import datetime
import pandas as pd
import pandas.io.data as web
from calc_rsi import calc_rsi

def test_calc_rsi():
    days = 30
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    stock_d = stock_tse.asfreq('B')[days:]
    rsi = calc_rsi(stock_d, n=14)
    result = rsi.ix['2014-10-30', 'Adj Close']
    expected = 55.935331193638028
    eq_(expected, result)
    return result

if __name__ == '__main__':
    print(test_calc_rsi())
