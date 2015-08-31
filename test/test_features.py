import sys
import os
import pandas as pd
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p not in sys.path:
    sys.path.append(p)
from features import Features
from ti import TechnicalIndicators

def testdata():
    days = 91
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    return stock_tse.asfreq('B')[days:]

def test_binary_class():
    stock_d = testdata()
    ti = TechnicalIndicators(stock_d)
    ti.calc_ret_index()

    ret_index = ti.stock['ret_index']
    f = Features()
    train_X, train_y = f.binary_class(ret_index, range=90)

    expected = [1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1,
                0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1,
                0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1,
                1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0,
                1, 1, 0]
    for r, e in zip(train_y, expected):
        eq_(r, e)

    r = round(train_X[-1][-1], 5)
    expected = 1.35486
    eq_(r, expected)

    r = round(train_X[0][0], 5)
    expected = 1.19213
    eq_(r, expected)

    expected = 14
    r = len(train_X[0])
    eq_(r, expected)

    expected = 75
    r = len(train_X)
    eq_(r, expected)

    train_X, train_y = f.binary_class(ret_index)

    expected = 0
    eq_(train_y[0], expected)

    expected = 1
    eq_(len(train_y), expected)

    r = round(train_X[0][0], 5)
    expected = 1.30311
    eq_(r, expected)

    expected = 14
    r = len(train_X[0])
    eq_(r, expected)

    expected = 1
    r = len(train_X)
    eq_(r, expected)

if __name__ == '__main__':
    test_binary_class()
