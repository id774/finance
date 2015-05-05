import sys
import os
import pandas as pd
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from ti import TechnicalIndicators
from analysis import Analysis

def testdata():
    days = 30
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    return stock_tse.asfreq('B')[days:]

def test_run():
    code = 'N225'
    name = '日経平均株価'
    start = '2014-01-01'
    days = 180
    csvfile = os.path.join(os.path.dirname(
        os.path.abspath(__file__)),
        '..',
        'test',
        'stock_N225.csv')
    update = False

    analysis = Analysis(code=code,
                        name=name,
                        start=start,
                        days=days,
                        csvfile=csvfile,
                        update=update)
    ti = analysis.run()
    expected = 18791.39
    result = round(ti.stock.ix['2015-03-20', 'sma25'], 2)
    eq_(expected, result)

    filename = 'ti_N225.csv'
    expected = True
    eq_(expected, os.path.exists(filename))
    if os.path.exists(filename):
        os.remove(filename)

    filename = 'chart_N225.png'
    expected = True
    eq_(expected, os.path.exists(filename))
    if os.path.exists(filename):
        os.remove(filename)

    return result

if __name__ == '__main__':
    test_run()
