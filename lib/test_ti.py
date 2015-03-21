from nose.tools import *
from ti import *

def test_get_macd():
    ti = TechnicalIndicators()
    ema_12 = 29.24
    ema_26 = 28.21
    macd = ti.get_macd(ema_12, ema_26)
    eq_(str(round(macd, 2)), "1.03")

def test_get_macd_ema():
    ti = TechnicalIndicators()
    macd_12_26_arr = [64.75, 63.79, 63.73, 63.73, 63.55, 63.19, 63.91, 63.85,
                      62.95, 63.37, 61.33, 61.51, 61.87, 60.25, 59.35, 59.95,
                      58.93, 57.68, 58.82, 58.87]
    macd_arr = []
    for macd in macd_12_26_arr:
        sp = StockPrice()
        sp.macd_12_26 = macd
        macd_arr.append(sp)
    signals = []
    prev_signal = 0
    for x, m in enumerate(macd_arr):
        tmp_signal = ti.get_macd_ema(macd_arr, x, 9, prev_signal)
        prev_signal = tmp_signal
        signals.append(tmp_signal)
    eq_(str(round(signals[14], 3)), "61.608")

def test_get_macd_histogram():
    ti = TechnicalIndicators()
    macd = 1.01
    ema_9 = 0.88
    macd_hist = ti.get_macd_histogram(macd, ema_9)
    eq_(str(round(macd_hist, 2)), "0.13")
