import sys
import os
from datetime import datetime
import pandas as pd
from pandas_datareader import data
p = os.path.dirname(os.path.abspath(__file__))
if p not in sys.path:
    sys.path.append(p)
from jpstock import JpStock
from get_logger import Logger

class FileIO():

    def __init__(self):
        self.logger = Logger()

    def save_data(self, df, stock, prefix):
        if not df.empty:
            df.to_csv("".join([prefix, stock, ".csv"]),
                      sep=",", index_label="Date")

    def read_from_csv(self, stock, filename):
        if os.path.exists(filename):
            return pd.read_csv(filename,
                               index_col=0, parse_dates=True)
        else:
            return self._read_with_jpstock(stock,
                                           start='2014-10-01')

    def _read_from_web(self, stock, start, end):
        start = datetime.strptime(start, '%Y-%m-%d')
        try:
            df = data.DataReader("".join(['^', stock]),
                                 'yahoo', start, end)
            if len(df) > 0:
                return df
            else:
                return pd.DataFrame([])
        except Exception as e:
            self.logger.error("".join(["Exception occured in ",
                                       stock, " at read_from_web"]))
            self.logger.error("".join(['ErrorType: ', str(type(e))]))
            self.logger.error("".join(['ErrorMessage: ', str(e)]))
            return pd.DataFrame([])

    def _read_with_jpstock(self, stock, start):
        try:
            jpstock = JpStock()
            df = jpstock.get(int(stock), start=start)
            if len(df) > 0:
                return df
            else:
                return pd.DataFrame([])
        except Exception as e:
            self.logger.error("".join(["Exception occured in ",
                                       stock, " at read_with_jpstock"]))
            self.logger.error("".join(['ErrorType: ', str(type(e))]))
            self.logger.error("".join(['ErrorMessage: ', str(e)]))
            return pd.DataFrame([])

    def read_data(self, stock, start, end):
        if stock in {'N225', 'GSPC', 'IXIC', 'DJI'}:
            return self._read_from_web(stock, start, end)
        else:
            return self._read_with_jpstock(stock, start)

    def merge_df(self, left, right):
        return pd.merge(left, right,
                        left_index=True, right_index=True)
