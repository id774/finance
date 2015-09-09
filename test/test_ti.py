import sys
import os
import pandas as pd
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p not in sys.path:
    sys.path.append(p)
from ti import TechnicalIndicators

def testdata():
    days = 30
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    return stock_tse.asfreq('B')[days:]

def test_calc_sma():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    sma = ti.calc_sma()
    sma = ti.calc_sma(timeperiod=25)
    sma = ti.calc_sma(timeperiod=75)

    expected = [19453.,
                18791.,
                17902.]
    result = (sma.ix['2015-03-20', 'sma5'],
              sma.ix['2015-03-20', 'sma25'],
              sma.ix['2015-03-20', 'sma75'])
    result = [round(x, 0) for x in result]
    eq_(expected, result)
    return sma

def test_calc_ewma():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    ewma = ti.calc_ewma()
    ewma = ti.calc_ewma(span=25)
    ewma = ti.calc_ewma(span=75)

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

def test_calc_rsi():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    rsi = ti.calc_rsi(timeperiod=14)

    expected = 74.98
    result = rsi.ix['2015-03-20', 'rsi14']
    result = round(result, 2)
    eq_(expected, result)
    return rsi

def test_calc_mfi():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    mfi = ti.calc_mfi()

    expected = 62.47
    result = mfi.ix['2015-03-20', 'mfi14']
    result = round(result, 2)
    eq_(expected, result)
    return mfi

def test_calc_roc():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    roc = ti.calc_roc(timeperiod=10)

    expected = 3.11
    result = roc.ix['2015-03-20', 'roc10']
    result = round(result, 2)
    eq_(expected, result)
    return roc

def test_calc_cci():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    cci = ti.calc_cci()

    expected = 104.27
    result = cci.ix['2015-03-20', 'cci14']
    result = round(result, 2)
    eq_(expected, result)
    return cci

def test_calc_ultosc():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    ultosc = ti.calc_ultosc()

    expected = 72.56
    result = ultosc.ix['2015-03-20', 'ultosc']
    result = round(result, 2)
    eq_(expected, result)
    return ultosc

def test_calc_stoch():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    stoch = ti.calc_stoch()

    expected = 93.79
    result = stoch.ix['2015-03-20', 'slowk']
    result = round(result, 2)
    eq_(expected, result)

    expected = 93.32
    result = stoch.ix['2015-03-20', 'slowd']
    result = round(result, 2)
    eq_(expected, result)

    return stoch

def test_calc_stochf():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    stochf = ti.calc_stochf()

    expected = 98.46
    result = stochf.ix['2015-03-20', 'fastk']
    result = round(result, 2)
    eq_(expected, result)

    expected = 93.79
    result = stochf.ix['2015-03-20', 'fastd']
    result = round(result, 2)
    eq_(expected, result)

    return stochf

def test_calc_macd():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    macd = ti.calc_macd()

    expected = [383.,
                346.,
                37.]
    result = (macd.ix['2015-03-20', 'macd'],
              macd.ix['2015-03-20', 'macdsignal'],
              macd.ix['2015-03-20', 'macdhist'])
    result = [round(x, 0) for x in result]
    eq_(expected, result)
    return macd

def test_calc_momentum():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    mom = ti.calc_momentum(timeperiod=10)

    expected = 589.22
    result = mom.ix['2015-03-20', 'mom10']
    result = round(result, 2)
    eq_(expected, result)
    return mom

def test_calc_bbands():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    bbands = ti.calc_bbands()

    expected = [19661.0,
                19436.0,
                19210.0]
    result = (bbands.ix['2015-03-20', 'upperband'],
              bbands.ix['2015-03-20', 'middleband'],
              bbands.ix['2015-03-20', 'lowerband'])
    result = [round(x, 0) for x in result]
    eq_(expected, result)
    return bbands

def test_calc_sar():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    sar = ti.calc_sar()

    expected = 18896.79
    result = sar.ix['2015-03-20', 'sar']
    result = round(result, 2)
    eq_(expected, result)
    return sar

def test_calc_willr():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    willr = ti.calc_willr(timeperiod=14)

    expected = -0.53
    result = willr.ix['2015-03-20', 'willr14']
    result = round(result, 2)
    eq_(expected, result)
    return willr

def test_calc_tr():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    tr = ti.calc_tr()

    expected = 148.81
    result = tr.ix['2015-03-20', 'tr']
    result = round(result, 2)
    eq_(expected, result)

    expected = 0.76
    result = tr.ix['2015-03-20', 'vl']
    result = round(result, 2)
    eq_(expected, result)
    return tr

def test_calc_atr():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    atr = ti.calc_atr()

    expected = 208.40
    result = atr.ix['2015-03-20', 'atr']
    result = round(result, 2)
    eq_(expected, result)
    return atr

def test_calc_natr():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    natr = ti.calc_natr()

    expected = 1.07
    result = natr.ix['2015-03-20', 'natr']
    result = round(result, 2)
    eq_(expected, result)
    return natr

def test_calc_ret_index():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    ret_index = ti.calc_ret_index()

    expected = 1.36
    result = ret_index.ix['2015-03-20', 'ret_index']
    result = round(result, 2)
    eq_(expected, result)
    return ret_index

def test_calc_vol():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    rets = ti.calc_ret_index()
    vol = ti.calc_vol(rets['ret_index'])

    expected = 1.56
    result = vol.ix['2015-03-20', 'vol']
    result = round(result, 2)
    eq_(expected, result)
    return vol

def test_calc_volume_rate():
    stock = testdata()
    ti = TechnicalIndicators(stock)
    vr = ti.calc_volume_rate()

    expected = 21.84
    result = vr.ix['2015-03-19', 'v_rate']
    result = round(result, 2)
    eq_(expected, result)
    return vr

if __name__ == '__main__':
    stock = testdata()
    sma = test_calc_sma()
    ewma = test_calc_ewma()
    rsi = test_calc_rsi()
    mfi = test_calc_mfi()
    roc = test_calc_roc()
    cci = test_calc_cci()
    ultosc = test_calc_ultosc()
    stoch = test_calc_stoch()
    stochf = test_calc_stochf()
    macd = test_calc_macd()
    momentum = test_calc_momentum()
    bbands = test_calc_bbands()
    sar = test_calc_sar()
    willr = test_calc_willr()
    tr = test_calc_tr()
    atr = test_calc_atr()
    natr = test_calc_natr()
    rets = test_calc_ret_index()
    vol = test_calc_vol()
    vr = test_calc_volume_rate()
    stock = pd.merge(stock, sma,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, ewma,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, rsi,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, mfi,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, roc,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, cci,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, ultosc,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, stoch,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, stochf,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, macd,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, momentum,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, willr,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, sar,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, bbands,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, natr,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, rets,
                     left_index=True, right_index=True)
    stock = pd.merge(stock, vol, on='ret_index',
                     left_index=True, right_index=True)
    stock = pd.merge(stock, vr,
                     left_index=True, right_index=True)
    print(stock.tail(10))
