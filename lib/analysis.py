import sys
import os
from datetime import datetime, timedelta, timezone
import pandas as pd
p = os.path.dirname(os.path.abspath(__file__))
if p not in sys.path:
    sys.path.append(p)
from file_io import FileIO
from ti import TechnicalIndicators
from classifier import Classifier
from regression import Regression
from draw import Draw

class Analysis():

    def __init__(self, code="", name="", fullname="",
                 start='2014-10-01',
                 days=240, csvfile=None, update=False,
                 axis=2,
                 complexity=3):
        self.code = code
        self.name = name
        if isinstance(fullname, str):
            if fullname == "":
                self.fullname = name
            else:
                self.fullname = fullname
        else:
            self.fullname = name
        self.start = start
        self.end = datetime.now()
        self.minus_days = days * -1
        self.csvfile = csvfile
        self.update = update
        self.clffile = "".join(['clf_', code, '.pickle'])
        self.regfile = "".join(['reg_', code, '.pickle'])
        self.axis = axis
        self.complexity = complexity

    def run(self):
        io = FileIO()
        will_update = self.update

        JST = timezone(timedelta(hours=+9), 'JST')

        now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
        level = "[info]"
        msg = "".join([now, level, " ", "Start Analysis: ", self.code])
        print(msg)

        if self.csvfile:
            stock_tse = io.read_from_csv(self.code,
                                         self.csvfile)

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[info]"
            msg = "".join([now, level, " ", "Read data from csv: ", self.code,
                           " Records: ", str(len(stock_tse))])
            print(msg)

            if self.update and len(stock_tse) > 0:
                index = pd.date_range(start=stock_tse.index[-1],
                                      periods=2, freq='B')
                ts = pd.Series(None, index=index)
                next_day = ts.index[1]
                t = next_day.strftime('%Y-%m-%d')
                newdata = io.read_data(self.code,
                                       start=t,
                                       end=self.end)

                now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
                level = "[info]"
                msg = "".join([now, level, " ", "Read data from web: ", self.code,
                               " New records: ", str(len(newdata))])
                print(msg)

                if len(newdata) < 1:
                    will_update = False
                else:
                    print(newdata.ix[-1, :])

                stock_tse = stock_tse.combine_first(newdata)
                io.save_data(stock_tse, self.code, 'stock_')
        else:
            stock_tse = io.read_data(self.code,
                                     start=self.start,
                                     end=self.end)

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[info]"
            msg = "".join([now, level, " ", "Read data from web: ", self.code,
                           " Records: ", str(len(stock_tse))])
            print(msg)

        if stock_tse.empty:

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[warn]"
            msg = "".join([now, level, " ", "Data empty: ", self.code])
            print(msg)

            return None

        if not self.csvfile:
            io.save_data(stock_tse, self.code, 'stock_')

        try:
            stock_d = stock_tse.asfreq('B').dropna()[self.minus_days:]

            ti = TechnicalIndicators(stock_d)

            ti.calc_sma()
            ti.calc_sma(timeperiod=5)
            ti.calc_sma(timeperiod=25)
            ti.calc_sma(timeperiod=50)
            ti.calc_sma(timeperiod=75)
            ti.calc_sma(timeperiod=200)
            ewma = ti.calc_ewma(span=5)
            ewma = ti.calc_ewma(span=25)
            ewma = ti.calc_ewma(span=50)
            ewma = ti.calc_ewma(span=75)
            ewma = ti.calc_ewma(span=200)
            bbands = ti.calc_bbands()
            sar = ti.calc_sar()
            draw = Draw(self.code, self.fullname)

            ret = ti.calc_ret_index()
            ti.calc_vol(ret['ret_index'])
            rsi = ti.calc_rsi(timeperiod=9)
            rsi = ti.calc_rsi(timeperiod=14)
            mfi = ti.calc_mfi()
            roc = ti.calc_roc(timeperiod=10)
            roc = ti.calc_roc(timeperiod=25)
            roc = ti.calc_roc(timeperiod=50)
            roc = ti.calc_roc(timeperiod=75)
            roc = ti.calc_roc(timeperiod=150)
            ti.calc_cci()
            ultosc = ti.calc_ultosc()
            stoch = ti.calc_stoch()
            ti.calc_stochf()
            ti.calc_macd()
            willr = ti.calc_willr()
            ti.calc_momentum(timeperiod=10)
            ti.calc_momentum(timeperiod=25)
            tr = ti.calc_tr()
            ti.calc_atr()
            ti.calc_natr()
            vr = ti.calc_volume_rate()

            ret_index = ti.stock['ret_index']
            clf = Classifier(self.clffile)
            train_X, train_y = clf.train(ret_index, will_update)

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[info]"
            msg = "".join([now, level, " ", "Classifier Train Records: ", str(len(train_y))])
            print(msg)

            clf_result = clf.classify(ret_index)[0]

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[info]"
            msg = "".join([now, level, " ", "Classified: ", str(clf_result)])
            print(msg)

            ti.stock.ix[-1, 'classified'] = clf_result

            reg = Regression(self.regfile,
                             alpha=1,
                             regression_type="Ridge")
            train_X, train_y = reg.train(ret_index, will_update)

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[info]"
            msg = "".join([now, level, " ", "Regression Train Records: ", str(len(train_y))])
            print(msg)

            base = ti.stock_raw['Adj Close'][0]
            reg_result = int(reg.predict(ret_index, base)[0])

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[info]"
            msg = "".join([now, level, " ", "Predicted: ", str(reg_result)])
            print(msg)

            ti.stock.ix[-1, 'predicted'] = reg_result

            if will_update is True:
                io.save_data(io.merge_df(stock_d, ti.stock),
                             self.code, 'ti_')

            if self.minus_days < -300:
                _prefix = 'long'
            elif self.minus_days >= -60:
                _prefix = 'short'
            else:
                _prefix = 'chart'

            draw.plot(stock_d, _prefix, ewma, bbands, sar,
                      rsi, roc, mfi, ultosc, willr,
                      stoch, tr, vr,
                      clf_result, reg_result,
                      axis=self.axis,
                      complexity=self.complexity)

            now = datetime.now(JST).strftime("[%Y-%m-%dT%H:%M:%S+09:00]")
            level = "[info]"
            msg = "".join([now, level, " ", "Finish Analysis: ", self.code])
            print(msg)

            return ti

        except (ValueError, KeyError) as e:
            print("Error occured in", self.code, "at analysis.py")
            print('ErrorType:', str(type(e)))
            print('ErrorMessage:', str(e))
            return None
