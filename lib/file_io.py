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

    def read_data(self, stock, start, end, filename=None):
        if filename:
            stock_tse = pd.read_csv(filename,
                                    index_col=0, parse_dates=True)
        else:
            if stock == 'N225':
                start = datetime.datetime.strptime(start, '%Y-%m-%d')
                stock_tse = web.DataReader('^N225', 'yahoo', start, end)
            else:
                jpstock = JpStock()
                stock_tse = jpstock.get(int(stock), start=start)
        return stock_tse

    def merge_df(self, left, right):
        return pd.merge(left, right,
                        left_index=True, right_index=True)
