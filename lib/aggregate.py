import sys
import os
import pandas as pd
import datetime

class Aggregator():

    def __init__(self, stock_list, data_dir):
        self.stock_list = stock_list
        self.data_dir = data_dir
        self.ti_dic = self._aggregate()

    def _aggregate(self):
        ti_dic = {}
        stocks = pd.read_csv(self.stock_list, header=None)
        for s in stocks.values:
            _code = str(s[0])
            if _code not in {'N225', 'GSPC', 'IXIC', 'DJI'}:
                _name = str(s[1])
                _csvfile = os.path.join(self.data_dir,
                                        "".join(['ti_', _code, ".csv"]))
                if os.path.exists(_csvfile):
                    _stock_d = pd.read_csv(_csvfile,
                                           index_col=0, parse_dates=True)
                    ti_dic[(_code, _name)] = _stock_d
        return ti_dic

    def summarize(self, range=1, sortkey='Ratio',
                  ascending=False, screening_key=None):
        range = range * -1 - 1
        df = pd.DataFrame([])
        base_date = datetime.date.today() - datetime.timedelta(10)
        for k, _stock_d in self.ti_dic.items():
            last_date = _stock_d.index[-1].to_datetime().date()
            if last_date >= base_date:
                _code = str(k[0])
                _name = str(k[1])
                _start = int(_stock_d.ix[range, 'Adj Close'])
                _end = int(_stock_d.ix[-1, 'Adj Close'])
                _open = int(_stock_d.ix[-1, 'Open'])
                _high = int(_stock_d.ix[-1, 'High'])
                _low = int(_stock_d.ix[-1, 'Low'])
                _close = int(_stock_d.ix[-1, 'Adj Close'])
                _change = _end - _start
                _ratio = round((1 + _change) / _close * 100, 2)
                _classified = int(_stock_d.ix[-1, 'classified'])
                _predicted = int(_stock_d.ix[-1, 'predicted'])
                if screening_key:
                    _key = int(_stock_d.ix[-1, screening_key])
                    df[_code] = pd.Series([_open,
                                          _high, _low, _close,
                                          _change, _ratio,
                                          _key, _name])
                else:
                    df[_code] = pd.Series([_open,
                                          _high, _low, _close,
                                          _change, _ratio,
                                          _classified, _predicted,
                                          _name])
        if df.empty:
            return df
        else:
            if screening_key:
                df.index = ['Open',
                            'High', 'Low', 'Close',
                            'Change', 'Ratio',
                            screening_key, 'Name']
            else:
                df.index = ['Open',
                            'High', 'Low', 'Close',
                            'Change', 'Ratio',
                            'Trend', 'Pred',
                            'Name']
        return df.T.sort(sortkey, ascending=ascending)

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
            result = aggregator.summarize(range=2)
            print(result)
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
