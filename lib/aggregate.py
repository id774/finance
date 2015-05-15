import sys
import os
import pandas as pd

class Aggregator():

    def __init__(self, stock_list, data_dir):
        self.stock_list = stock_list
        self.data_dir = data_dir

    def summarize(self):
        stocks = pd.read_csv(self.stock_list, header=None)
        df = pd.DataFrame([])
        for s in stocks.values:
            _code = str(s[0])
            _name = str(s[1])
            _csvfile = os.path.join(self.data_dir,
                                    "".join(['stock_', _code, ".csv"]))
            if os.path.exists(_csvfile):
                _stock = pd.read_csv(_csvfile,
                                     index_col=0, parse_dates=True)
                _stock_d = _stock.asfreq('B').dropna()
                _open = int(_stock_d.ix[-1, 'Open'])
                _high = int(_stock_d.ix[-1, 'High'])
                _low = int(_stock_d.ix[-1, 'Low'])
                _close = int(_stock_d.ix[-1, 'Adj Close'])
                _last_close = int(_stock_d.ix[-2, 'Adj Close'])
                _close_diff = _close - _last_close
                _close_ratio = round((1 + _close_diff) / _close * 100, 2)
                df[_code] = pd.Series([_open, _high, _low, _close,
                                       _close_diff, _close_ratio,
                                       _name])
        df.index = ['Open', 'High', 'Low', 'Close',
                    'Diff', 'Ratio', 'Name']
        return df.T.sort('Ratio', ascending=False)

if __name__ == '__main__':
    argsmin = 0
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            c_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.join(c_dir, '..')
            data_dir = os.path.join(base_dir, 'data')
            stock_list = os.path.join(base_dir, 'data',
                                      'stocks.txt')
            aggregator = Aggregator(stock_list, data_dir)
            result = aggregator.summarize()
            print(result)
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
