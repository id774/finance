import sys
import os
import datetime
import pandas as pd
from pandas_datareader import data
p = os.path.dirname(os.path.abspath(__file__))
if p in sys.path:
    pass
else:
    sys.path.append(p)
from jpstock import JpStock

class FileIO():

    def save_data(self, df, stock, prefix):
        if df.empty:
            pass
        else:
            df.to_csv("".join([prefix, stock, ".csv"]))

    def read_from_csv(self, stock, filename):
        if os.path.exists(filename):
            return pd.read_csv(filename,
                               index_col=0, parse_dates=True)
        else:
            return self._read_with_jpstock(stock,
                                           start='2014-09-01')

    def _read_from_web(self, start, end):
        start = datetime.datetime.strptime(start, '%Y-%m-%d')
        return data.DataReader('^N225', 'yahoo', start, end)

    def _read_with_jpstock(self, stock, start):
        try:
            jpstock = JpStock()
            df = jpstock.get(int(stock), start=start)
            if len(df) > 0:
                return df
            else:
                return pd.DataFrame([])
        except:
            return pd.DataFrame([])

    def read_data(self, stock, start, end):
        if stock == 'N225':
            return self._read_from_web(start, end)
        else:
            return self._read_with_jpstock(stock, start)

    def merge_df(self, left, right):
        return pd.merge(left, right,
                        left_index=True, right_index=True)
