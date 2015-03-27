import sys
import os
import datetime
p = os.path.dirname(os.path.abspath(__file__))
if p in sys.path:
    pass
else:
    sys.path.append(p)
from file_io import FileIO
from ti import TechnicalIndicators
from draw import Draw

class Analysis():

    def __init__(self, stock="", name="", start='2014-09-01',
                 days=90, csvfile=None):
        self.stock = stock
        self.name = name
        self.start = start
        self.end = datetime.datetime.now()
        self.days = int(days) * -1
        self.csvfile = csvfile

    def run(self):
        io = FileIO()
        stock_tse = io.read_data(self.stock,
                                 start=self.start,
                                 end=self.end,
                                 csvfile=self.csvfile)

        if stock_tse.empty:
            print("Data empty", self.stock)
            return None

        if not self.csvfile:
            io.save_data(stock_tse, self.stock, 'stock_')

        try:
            stock_d = stock_tse.asfreq('B')[self.days:]

            ti = TechnicalIndicators(stock_d)

            # sma = ti.get_sma()
            # sma = ti.get_sma(timeperiod=25)
            # sma = ti.get_sma(timeperiod=75)
            ewma = ti.get_ewma(span=5)
            ewma = ti.get_ewma(span=25)
            ewma = ti.get_ewma(span=75)
            bbands = ti.get_bbands()
            draw = Draw(self.stock, self.name)
            draw.plot_ohlc(stock_d, ewma, bbands)

            rsi = ti.get_rsi(timeperiod=9)
            rsi = ti.get_rsi(timeperiod=14)
            macd = ti.get_macd()
            draw.plot_osci(rsi, macd)

            io.save_data(io.merge_df(stock_d, ti.get_data()),
                         self.stock, 'ti_')

        except (ValueError, KeyError):
            print("Error occured in", stock)
