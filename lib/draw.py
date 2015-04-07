import sys
import os
import pandas.tools.plotting as plotting
import matplotlib.pyplot as plt
from matplotlib import font_manager
p = os.path.dirname(os.path.abspath(__file__))
if p in sys.path:
    pass
else:
    sys.path.append(p)
from ohlc_plot import OhlcPlot

class Draw():

    def __init__(self, stock, name, **kwargs):
        self.stock = stock
        self.name = name
        self.fontprop = font_manager.FontProperties(
            fname="/usr/share/fonts/truetype/fonts-japanese-gothic.ttf")

    def plot_ohlc(self, stock_d, ewma, bbands):
        plotting._all_kinds.append('ohlc')
        plotting._common_kinds.append('ohlc')
        plotting._plot_klass['ohlc'] = OhlcPlot

        plt.figure()
        stock_d.plot(kind='ohlc', colorup='r', colordown='k')
        # sma['sma5'].plot(label="SMA5")
        # sma['sma25'].plot(label="SMA25")
        # sma['sma75'].plot(label="SMA75")
        ewma['ewma5'].plot(label="EWMA5", color="b")
        ewma['ewma25'].plot(label="EWMA25", color="g")
        ewma['ewma75'].plot(label="EWMA75", color="r")
        bbands['upperband'].plot(label="UPPER", color="c")
        bbands['middleband'].plot(label="MIDDLE", color="m")
        bbands['lowerband'].plot(label="LOWER", color="y")
        plt.subplots_adjust(bottom=0.20)
        closed = stock_d.ix[-1:, 'Adj Close'][0]
        plt.xlabel("".join(
                   [self.name, '(', self.stock, '):',
                    str(closed)]),
                   fontdict={"fontproperties": self.fontprop})
        plt.legend(loc="best")
        plt.show()
        plt.savefig("".join(["ohlc_", self.stock, ".png"]))
        plt.close()

    def plot_osci(self, ret, rsi, mfi, ultosc,
                  stoch, stochf, vr):
        plt.figure()
        ret['ret_index'].plot(label="RET_INDEX", color="b")
        rsi['rsi9'].plot(label="RSI9", color="g")
        rsi['rsi14'].plot(label="RSI14", color="r")
        rsi['mfi'].plot(label="MFI", color="c")
        rsi['ultosc'].plot(label="UTLOSC", color="m")
        stoch['slowk'].plot(label="SLOWK", color="y")
        stoch['slowd'].plot(label="SLOWD", color="k")
        vr['v_ratio'].plot(label="VOLUME", color="#00DDFF")
        # stochf['fastk'].plot(label="FASTK")
        # stochf['fastd'].plot(label="FASTD")
        plt.subplots_adjust(bottom=0.20)
        ret_index = round(ret.ix[-1:, 'ret_index'][0], 2)
        plt.xlabel("".join(
                   [self.name, '(', self.stock, '):',
                    str(ret_index)]),
                   fontdict={"fontproperties": self.fontprop})
        # plt.ylim = (np.arange(0, 110, step=10))
        plt.ylim = ([0, 100])
        plt.legend(loc="best")
        plt.show()
        plt.savefig("".join(["osci_", self.stock, ".png"]))
        plt.legend(loc="best")
        plt.close()
