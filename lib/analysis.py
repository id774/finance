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
from classifier import Classifier
from draw import Draw

class Analysis():

    def __init__(self, stock="", name="", start='2014-10-01',
                 days=120, csvfile=None, update=False):
        self.stock = stock
        self.name = name
        self.start = start
        self.end = datetime.datetime.now()
        self.days = int(days) * -1
        self.csvfile = csvfile
        self.update = update
        self.clffile = "".join(['clf_', stock, '.pickle'])

    def run(self):
        io = FileIO()
        will_update = self.update

        if self.csvfile:
            stock_tse = io.read_from_csv(self.stock,
                                         self.csvfile)

            msg = "".join(["Read data from csv: ", self.stock,
                           " Records: ", str(len(stock_tse))])
            print(msg)

            if self.update and len(stock_tse) > 0:
                t = stock_tse.index[-1].strftime('%Y-%m-%d')
                newdata = io.read_data(self.stock,
                                       start=t,
                                       end=self.end)

                msg = "".join(["Read data from web: ", self.stock,
                               " New records: ", str(len(newdata))])
                print(msg)
                if len(newdata) < 2:
                    will_update = False

                stock_tse = stock_tse.combine_first(newdata)
                io.save_data(stock_tse, self.stock, 'stock_')
        else:
            stock_tse = io.read_data(self.stock,
                                     start=self.start,
                                     end=self.end)

            msg = "".join(["Read data from web: ", self.stock,
                           " Records: ", str(len(stock_tse))])
            print(msg)

        if stock_tse.empty:
            msg = "".join(["Data empty: ", self.stock])
            print(msg)
            return None

        if not self.csvfile:
            io.save_data(stock_tse, self.stock, 'stock_')

        try:
            stock_d = stock_tse.asfreq('B')[self.days:]

            ti = TechnicalIndicators(stock_d)

            ti.calc_sma()
            ti.calc_sma(timeperiod=25)
            ti.calc_sma(timeperiod=75)
            ewma = ti.calc_ewma(span=5)
            ewma = ti.calc_ewma(span=25)
            ewma = ti.calc_ewma(span=75)
            bbands = ti.calc_bbands()
            draw = Draw(self.stock, self.name)

            ret = ti.calc_ret_index()
            ret['ret_index'] = ret['ret_index'] * 100
            rsi = ti.calc_rsi(timeperiod=9)
            rsi = ti.calc_rsi(timeperiod=14)
            mfi = ti.calc_mfi()
            ti.calc_roc()
            ti.calc_cci()
            ultosc = ti.calc_ultosc()
            stoch = ti.calc_stoch()
            ti.calc_stochf()
            ti.calc_macd()
            ti.calc_momentum(timeperiod=10)
            ti.calc_momentum(timeperiod=25)
            ti.calc_natr()
            vr = ti.calc_volume_ratio()

            clf = Classifier(self.clffile)
            ret_index = ti.stock['ret_index']
            train_X, train_y = clf.train(ret_index, will_update)
            msg = "".join(["Train Records: ", str(len(train_y))])
            print(msg)
            clf_result = clf.classify(ret_index)
            msg = "".join(["Classified: ", str(clf_result[0])])
            print(msg)

            draw.plot(stock_d, ewma, bbands,
                      ret, rsi, mfi, ultosc,
                      stoch, vr,
                      clf_result[0])

            io.save_data(io.merge_df(stock_d, ti.stock),
                         self.stock, 'ti_')

            return ti

        except (ValueError, KeyError):
            msg = "".join(["Error occured in ", self.stock])
            print(msg)
            return None
