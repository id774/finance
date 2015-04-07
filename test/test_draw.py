import sys
import os
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from draw import Draw
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

def test_plot_ohlc():
    stock = testdata()
    draw = Draw("N225", "日経平均株価")

    ti = TechnicalIndicators(stock)
    ewma = ti.calc_ewma(span=5)
    ewma = ti.calc_ewma(span=25)
    ewma = ti.calc_ewma(span=75)
    bbands = ti.calc_bbands()
    draw.plot_ohlc(stock, ewma, bbands)

    filename = 'ohlc_N225.png'
    expected = True
    eq_(expected, os.path.exists(filename))

    if os.path.exists(filename):
        os.remove(filename)

def test_plot_osci():
    stock = testdata()
    draw = Draw("N225", "日経平均株価")

    ti = TechnicalIndicators(stock)
    ret = ti.calc_ret_index()
    rsi = ti.calc_rsi(timeperiod=9)
    rsi = ti.calc_rsi(timeperiod=14)
    mfi = ti.calc_mfi()
    ultosc = ti.calc_ultosc()
    stoch = ti.calc_stoch()
    stochf = ti.calc_stochf()
    vr = ti.calc_volume_ratio()
    draw.plot_osci(ret, rsi, mfi, ultosc,
                   stoch, stochf, vr)

    filename = 'osci_N225.png'
    expected = True
    eq_(expected, os.path.exists(filename))

    if os.path.exists(filename):
        os.remove(filename)
