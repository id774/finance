import sys
import datetime
import pandas as pd
import pandas.io.data as web

def calc_rsi(price, n=14):
    ''' Relative Strength Index '''

    # calculate price gain with previous day, first row nan is filled with 0
    gain = (price - price.shift(1)).fillna(0)

    def rsiCalc(p):
        ''' subfunction for calculating rsi for one lookback period '''
        avgGain = p[p > 0].sum() / n
        avgLoss = -p[p < 0].sum() / n
        rs = avgGain / avgLoss
        return 100 - 100 / (1 + rs)

    # run for all periods with rolling_apply
    return pd.rolling_apply(gain, n, rsiCalc)


if __name__ == '__main__':
    argsmin = 0
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            days = 30
            start = '2014-09-01'
            end = datetime.datetime.now()
            start = datetime.datetime.strptime(start, '%Y-%m-%d')
            stock_tse = web.DataReader('^N225', 'yahoo', start, end)
            stock_d = stock_tse.asfreq('B')[days:]
            rsi = calc_rsi(stock_d, n=14)
            print(rsi)
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
