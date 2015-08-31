import sys
import os
import pandas as pd
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p not in sys.path:
    sys.path.append(p)
from ti import TechnicalIndicators
from regression import Regression

def testdata():
    days = 91
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    return stock_tse.asfreq('B')[days:]

def test_ridge_regression():
    stock_d = testdata()
    ti = TechnicalIndicators(stock_d)

    filename = 'test_N225_ridge.pickle'
    clffile = os.path.join(os.path.dirname(
                           os.path.abspath(__file__)),
                           '..', 'clf',
                           filename)

    if os.path.exists(clffile):
        os.remove(clffile)

    clf = Regression(filename)
    ti.calc_ret_index()
    ret = ti.stock['ret_index']
    base = ti.stock_raw['Adj Close'][0]

    train_X, train_y = clf.train(ret, regression_type="Ridge")

    test_y = clf.predict(ret, base)

    expected = 19177.97
    r = round(test_y[0], 2)
    eq_(r, expected)

    if os.path.exists(clffile):
        os.remove(clffile)

if __name__ == '__main__':
    test_ridge_regression()
