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
from ochl_plot import OchlPlot

class Draw():

    def __init__(self, stock, name, **kwargs):
        self.stock = stock
        self.name = name
        self.fontprop = font_manager.FontProperties(
            fname="/usr/share/fonts/truetype/fonts-japanese-gothic.ttf")

    def plot_ochl(self, stock_d, ewma, bbands):
        plotting._all_kinds.append('ochl')
        plotting._common_kinds.append('ochl')
        plotting._plot_klass['ochl'] = OchlPlot

        plt.figure()
        stock_d.plot(kind='ochl')
        # sma['sma5'].plot(label="SMA5")
        # sma['sma25'].plot(label="SMA25")
        # sma['sma75'].plot(label="SMA75")
        ewma['ewma5'].plot(label="EWMA5")
        ewma['ewma25'].plot(label="EWMA25")
        ewma['ewma75'].plot(label="EWMA75")
        bbands['upperband'].plot(label="UPPER")
        bbands['middleband'].plot(label="MIDDLE")
        bbands['lowerband'].plot(label="LOWER")
        plt.subplots_adjust(bottom=0.20)
        closed = stock_d.ix[-1:, 'Adj Close'][0]
        plt.xlabel("".join(
                   [self.name, '(', self.stock, '):',
                    str(closed)]),
                   fontdict={"fontproperties": self.fontprop})
        plt.legend(loc="best")
        plt.show()
        plt.savefig("".join(["ochl_", self.stock, ".png"]))
        plt.close()

    def plot_osci(self, rsi, macd, mom):
        plt.figure()
        rsi['rsi9'].plot(label="RSI9")
        rsi['rsi14'].plot(label="RSI14")
        macd['macd'].plot(label="MACD")
        macd['macdsignal'].plot(label="MACD-SIGNAL")
        macd['macdhist'].plot(label="MACD-HIST")
        mom['mom10'].plot(label="MOM10")
        mom['mom25'].plot(label="MOM25")
        plt.subplots_adjust(bottom=0.20)
        closed = round(rsi.ix[-1:, 'rsi14'][0], 2)
        plt.xlabel("".join(
                   [self.name, '(', self.stock, '):',
                    str(closed)]),
                   fontdict={"fontproperties": self.fontprop})
        # plt.ylim = (np.arange(0, 110, step=10))
        plt.ylim = ([0, 100])
        plt.legend(loc="best")
        plt.show()
        plt.savefig("".join(["osci_", self.stock, ".png"]))
        plt.legend(loc="best")
        plt.close()
