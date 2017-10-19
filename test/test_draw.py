import sys
import os
import pandas as pd
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p not in sys.path:
    sys.path.append(p)
from draw import Draw
from ti import TechnicalIndicators

def testdata():
    days = 30
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    return stock_tse.asfreq('B')[days:]

def test_plot():
    stock = testdata()
    draw = Draw("N225", "日経平均株価")

    ti = TechnicalIndicators(stock)

    rsi = ti.calc_rsi(timeperiod=9)
    rsi = ti.calc_rsi(timeperiod=14)
    roc = ti.calc_roc()
    roc = ti.calc_roc(timeperiod=25)
    mfi = ti.calc_mfi()
    ultosc = ti.calc_ultosc()
    stoch = ti.calc_stoch()
    willr = ti.calc_willr()
    tr = ti.calc_tr()
    vr = ti.calc_volume_rate()

    ewma = ti.calc_ewma(span=5)
    ewma = ti.calc_ewma(span=25)
    ewma = ti.calc_ewma(span=50)
    ewma = ti.calc_ewma(span=75)
    ewma = ti.calc_ewma(span=200)
    bbands = ti.calc_bbands()
    sar = ti.calc_sar()

    draw.plot(stock, 'test', ewma, bbands, sar,
              rsi, roc, mfi, ultosc, willr,
              stoch, tr, vr,
              clf_result=0, reg_result=5000)

    eq_(draw.code, 'N225')
    eq_(draw.name, '日経平均株価')

    filename = 'test_N225.png'
    expected = True
    eq_(expected, os.path.exists(filename))

    if os.path.exists(filename):
        os.remove(filename)

if __name__ == '__main__':
    test_plot()
