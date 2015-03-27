import sys
import os
import datetime
import pandas as pd
import pandas.io.data as web
p = os.path.dirname(os.path.abspath(__file__))
if p in sys.path:
    pass
else:
    sys.path.append(p)
from jpstock import JpStock

class FileIO():

    def save_data(self, df, stock, prefix):
        df.to_csv("".join([prefix, stock, ".csv"]))

    def _read_from_csv(self, filename):
        return pd.read_csv(filename,
                           index_col=0, parse_dates=True)

    def _read_from_web(self, start, end):
        start = datetime.datetime.strptime(start, '%Y-%m-%d')
        return web.DataReader('^N225', 'yahoo', start, end)

    def _read_with_jpstock(self, stock, start):
        try:
            jpstock = JpStock()
            return jpstock.get(int(stock), start=start)
        except:
            print("Error occured in", stock)
            return pd.DataFrame([])

    def read_data(self, stock, start, end, csvfile=None):
        if csvfile:
            df = self._read_from_csv(csvfile)
        else:
            if stock == 'N225':
                df = self._read_from_web(start, end)
            else:
                df = self._read_with_jpstock(stock, start)
        return df

    def merge_df(self, left, right):
        return pd.merge(left, right,
                        left_index=True, right_index=True)
