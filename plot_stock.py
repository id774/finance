import sys
import os
import datetime
import pandas as pd
import pandas.tools.plotting as plotting
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'lib'))
from file_io import FileIO
from ohlc_plot import OhlcPlot
from ti import TechnicalIndicators

def _plot_stock(stock="", name="", start='2014-09-01', days=0, filename=None):
    plotting._all_kinds.append('ohlc')
    plotting._common_kinds.append('ohlc')
    plotting._plot_klass['ohlc'] = OhlcPlot
    fontprop = font_manager.FontProperties(
        fname="/usr/share/fonts/truetype/fonts-japanese-gothic.ttf")

    end = datetime.datetime.now()

    if not days:
        days = 90
    else:
        days = int(days)
    days = days * -1

    io = FileIO()
    stock_tse = io.read_data(stock,
                             start=start,
                             end=end,
                             filename=filename)
    if stock_tse.empty:
        return None
    if not filename:
        io.save_data(stock_tse, stock, 'stock_')

    try:
        stock_d = stock_tse.asfreq('B')[days:]

        plt.figure()
        ti = TechnicalIndicators(stock_d)

        stock_d.plot(kind='ohlc')

        # sma = ti.get_sma()
        # sma = ti.get_sma(timeperiod=25)
        # sma = ti.get_sma(timeperiod=75)
        # sma['sma5'].plot(label="SMA5")
        # sma['sma25'].plot(label="SMA25")
        # sma['sma75'].plot(label="SMA75")
        ewma = ti.get_ewma(span=5)
        ewma = ti.get_ewma(span=25)
        ewma = ti.get_ewma(span=75)
        ewma['ewma5'].plot(label="EWMA5")
        ewma['ewma25'].plot(label="EWMA25")
        ewma['ewma75'].plot(label="EWMA75")
        bbands = ti.get_bbands()
        bbands['boll_upper'].plot(label="UPPER")
        bbands['boll_middle'].plot(label="MIDDLE")
        bbands['boll_lower'].plot(label="LOWER")

        plt.subplots_adjust(bottom=0.20)
        closed = stock_d.ix[-1:, 'Adj Close'][0]
        plt.xlabel("".join(
                   [name, '(', stock, '):',
                    str(closed)]),
                   fontdict={"fontproperties": fontprop})
        plt.legend(loc="best")
        plt.show()
        plt.savefig("".join(["ohlc_", stock, ".png"]))
        plt.close()

        plt.figure()

        rsi = ti.get_rsi(timeperiod=9)
        rsi = ti.get_rsi(timeperiod=14)
        rsi['rsi9'].plot(label="RSI9")
        rsi['rsi14'].plot(label="RSI14")
        macd = ti.get_macd()
        macd['macd'].plot(label="MACD")
        macd['macdsignal'].plot(label="MACD-SIGNAL")
        macd['macdhist'].plot(label="MACD-HIST")

        plt.subplots_adjust(bottom=0.20)

        closed = round(rsi.ix[-1:, 'rsi14'][0], 2)
        plt.xlabel("".join(
                   [name, '(', stock, '):',
                    str(closed)]),
                   fontdict={"fontproperties": fontprop})
        # plt.ylim = (np.arange(0, 110, step=10))
        plt.ylim = ([0, 100])
        plt.legend(loc="best")
        plt.show()
        plt.savefig("".join(["osci_", stock, ".png"]))
        plt.legend(loc="best")
        plt.close()
        io.save_data(io.merge_df(stock_d, ti.get_data()),
                     stock, 'ti_')

    except (ValueError, KeyError):
        print("Error occured in", stock)

def read_csv(filename, start, days):
    stocks = pd.read_csv(filename, header=True)
    for s in stocks.values:
        _plot_stock(stock=str(s[0]),
                    name=s[1],
                    start=start,
                    days=days)

def main():
    from optparse import OptionParser
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-c", "--code", dest="stockcode",
                      help="stock code")
    parser.add_option("-n", "--name", dest="stockname",
                      help="stock name")
    parser.add_option("-s", "--stock", dest="stocktxt",
                      help="read scraping stock names from text file")
    parser.add_option("-r", "--readfile", dest="csvfile",
                      help="read stock data from csv file")
    parser.add_option("-d", "--date", dest="startdate",
                      help="specify start date as '2014-09-01'")
    parser.add_option("-y", "--days", dest="days",
                      help="plot days as '-90', specify 0 for all days")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    if options.stocktxt:
        read_csv(filename=options.stocktxt,
                 start=options.startdate,
                 days=options.days)
    else:
        _plot_stock(stock=options.stockcode,
                    name=options.stockname,
                    filename=options.csvfile,
                    start=options.startdate,
                    days=options.days)

if __name__ == '__main__':
    argsmin = 0
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            main()
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
