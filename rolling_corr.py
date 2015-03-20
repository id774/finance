import sys
import pandas as pd
import matplotlib.pyplot as plt

def rolling_corr_with_N225(stock, window=5):
    d1 = pd.read_csv("".join(["stock_", stock, ".csv"]), index_col=0, parse_dates=True)
    d2 = pd.read_csv("stock_N225.csv", index_col=0, parse_dates=True)
    s1 = d1.asfreq('B')['Adj Close'].pct_change().dropna()
    s2 = d2.asfreq('B')['Adj Close'].pct_change().dropna()
    rolling_corr = pd.rolling_corr(s1, s2, window).dropna()

    plt.figure()
    rolling_corr.plot()
    plt.savefig("".join(["corr_", stock, ".png"]))
    plt.close()

    return rolling_corr

if __name__ == '__main__':
    argsmin = 1
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            result = rolling_corr_with_N225(sys.argv[1])
            print(result)
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
