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

    def __init__(self, code="", name="", start='2014-09-01',
                 days=180, csvfile=None, update=False):
        self.code = code
        self.name = name
        self.start = start
        self.end = datetime.datetime.now()
        self.days = int(days) * -1
        self.csvfile = csvfile
        self.update = update
        self.clffile = "".join(['clf_', code, '.pickle'])

    def run(self):
        io = FileIO()
        will_update = self.update

        if self.csvfile:
            stock_tse = io.read_from_csv(self.code,
                                         self.csvfile)

            msg = "".join(["Read data from csv: ", self.code,
                           " Records: ", str(len(stock_tse))])
            print(msg)

            if self.update and len(stock_tse) > 0:
                t = stock_tse.index[-1].strftime('%Y-%m-%d')
                newdata = io.read_data(self.code,
                                       start=t,
                                       end=self.end)

                msg = "".join(["Read data from web: ", self.code,
                               " New records: ", str(len(newdata))])
                print(msg)
                if len(newdata) < 2:
                    will_update = False

                stock_tse = stock_tse.combine_first(newdata)
                io.save_data(stock_tse, self.code, 'stock_')
        else:
            stock_tse = io.read_data(self.code,
                                     start=self.start,
                                     end=self.end)

            msg = "".join(["Read data from web: ", self.code,
                           " Records: ", str(len(stock_tse))])
            print(msg)

        if stock_tse.empty:
            msg = "".join(["Data empty: ", self.code])
            print(msg)
            return None

        if not self.csvfile:
            io.save_data(stock_tse, self.code, 'stock_')

        try:
            stock_d = stock_tse.asfreq('B').dropna()[self.days:]

            ti = TechnicalIndicators(stock_d)

            ti.calc_sma()
            ti.calc_sma(timeperiod=25)
            ti.calc_sma(timeperiod=75)
            ewma = ti.calc_ewma(span=5)
            ewma = ti.calc_ewma(span=25)
            ewma = ti.calc_ewma(span=75)
            bbands = ti.calc_bbands()
            draw = Draw(self.code, self.name)

            ret = ti.calc_ret_index()
            ti.calc_vol(ret['ret_index'])
            rsi = ti.calc_rsi(timeperiod=9)
            rsi = ti.calc_rsi(timeperiod=14)
            mfi = ti.calc_mfi()
            roc = ti.calc_roc(timeperiod=10)
            roc = ti.calc_roc(timeperiod=25)
            ti.calc_cci()
            ultosc = ti.calc_ultosc()
            stoch = ti.calc_stoch()
            ti.calc_stochf()
            ti.calc_macd()
            ti.calc_momentum(timeperiod=10)
            ti.calc_momentum(timeperiod=25)
            tr = ti.calc_tr()
            ti.calc_atr()
            ti.calc_natr()
            vr = ti.calc_volume_rate()

            clf = Classifier(self.clffile)
            ret_index = ti.stock['ret_index']
            train_X, train_y = clf.train(ret_index, will_update)
            msg = "".join(["Train Records: ", str(len(train_y))])
            print(msg)
            clf_result = clf.classify(ret_index)
            msg = "".join(["Classified: ", str(clf_result[0])])
            print(msg)

            io.save_data(io.merge_df(stock_d, ti.stock),
                         self.code, 'ti_')

            draw.plot(stock_d, ewma, bbands,
                      ret, rsi, roc, mfi, ultosc,
                      stoch, tr, vr,
                      clf_result[0],
                      axis=2)

            return ti

        except (ValueError, KeyError):
            msg = "".join(["Error occured in ", self.code])
            print(msg)
            return None
