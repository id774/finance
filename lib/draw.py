import sys
import os
import datetime
try:
    import pandas.plotting._core as plotting
except ImportError:
    import pandas.tools.plotting as plotting
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
p = os.path.dirname(os.path.abspath(__file__))
if p not in sys.path:
    sys.path.append(p)
from ohlc_plot import OhlcPlot

class Draw():

    def __init__(self, code, name, **kwargs):
        self.code = code
        self.name = name
        if sys.platform == "darwin":
            if os.path.exists("/Library/Fonts/Osaka.ttf"):
                font_path = "/Library/Fonts/Osaka.ttf"
            else:
                font_path = "/Library/Fonts/Arial.ttf"
        else:
            font_path = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
        self.fontprop = font_manager.FontProperties(
            fname=font_path)

    def plot(self, stock_d, prefix, ewma, bbands, sar,
             rsi, roc, mfi, ultosc, willr,
             stoch, tr, vr,
             clf_result, reg_result,
             axis=2, complexity=3):

        plotting._all_kinds.append('ohlc')
        plotting._common_kinds.append('ohlc')
        plotting._plot_klass['ohlc'] = OhlcPlot

        fig = plt.figure(figsize=(12.80, 10.24))

        if axis >= 2:
            ax1 = fig.add_subplot(2, 1, 1)
        else:
            ax1 = fig.add_subplot(1, 1, 1)

        if complexity >= 2:
            ewma['ewma5'].plot(label="MA5",
                               color="k", ax=ax1, grid=True)
        ewma['ewma25'].plot(label="MA25",
                            color="g", ax=ax1, grid=True)
        ewma['ewma50'].plot(label="MA50",
                            color="m", ax=ax1, grid=True)
        ewma['ewma75'].plot(label="MA75",
                            color="r", ax=ax1, grid=True)
        if complexity < 2:
            ewma['ewma200'].plot(label="MA200",
                                 color="k", ax=ax1, grid=True)
        if complexity >= 3:
            bbands['upperband'].plot(label="UPPER",
                                     color="c", ax=ax1, grid=True)
            bbands['lowerband'].plot(label="LOWER",
                                     color="y", ax=ax1, grid=True)
        if complexity >= 2:
            sar['sar'].plot(linestyle=':', label="SAR",
                            color="#FF0088", ax=ax1, grid=True)
        if axis == 1:
            vr['v_rate_p'].plot(linestyle=':', label="VOLUME",
                                color="#444444", ax=ax1, grid=True)
        stock_d.plot(kind='ohlc',
                     colorup='r', colordown='b',
                     ax=ax1, grid=True)
        ncol = complexity + 1

        if axis >= 2:
            plt.legend(loc='upper center', bbox_to_anchor=(0.36, 1.228),
                       ncol=ncol, fancybox=False, shadow=False)

            tr['vl'] = tr['vl'] * 5

            ax2 = fig.add_subplot(2, 1, 2)
            rsi['rsi9'].plot(label="RSI9",
                             color="b", ax=ax2)
            rsi['rsi14'].plot(label="RSI14",
                              color="k", ax=ax2)
            if complexity >= 3:
                roc['roc10'] = roc['roc10'] + 50
                roc['roc25'] = roc['roc25'] + 50
                roc['roc10'].plot(label="ROC10",
                                  color="g", ax=ax2)
                roc['roc25'].plot(label="ROC25",
                                  color="r", ax=ax2, grid=True)
            if complexity >= 2:
                mfi['mfi14'].plot(label="MFI",
                                  color="#DD88DD", ax=ax2, grid=True)
                ultosc['ultosc'].plot(label="UO",
                                      color="m", ax=ax2, grid=True)
                stoch['slowk'].plot(label="SLOWK",
                                    color="y", ax=ax2, grid=True)
                stoch['slowd'].plot(label="SLOWD",
                                    color="#888888", ax=ax2, grid=True)
            if complexity >= 3:
                willr['willr14'] = willr['willr14'] + 100
                willr['willr14'].plot(label="%R",
                                      color="#BBBBFF", ax=ax2, grid=True)
            tr['vl'].plot(label="VL",
                          color="c", ax=ax2, grid=True)
            vr['v_rate'].plot(label="VOLUME", kind='area',
                              color="#DDFFFF", ax=ax2, grid=True)

            ax2.set_yticks([0, 25, 50, 75, 100])

        _volume = int(stock_d.ix[-1, 'Volume'])
        _close = int(stock_d.ix[-1, 'Adj Close'])
        _last_close = int(stock_d.ix[-2, 'Adj Close'])
        _stock_max = int(stock_d.ix[:, 'High'].max())
        _stock_min = int(stock_d.ix[:, 'Low'].min())
        _close_change = _close - _last_close
        _close_ratio = round((1 + _close_change) / _close * 100, 2)
        if _close_change >= 0:
            _close_change = "".join(['+', str(_close_change)])
        else:
            _close_change = str(_close_change)
        if clf_result == 0:
            _clf_result = "↓"
        else:
            _clf_result = "↑"

        today = datetime.datetime.today().strftime("%Y/%m/%d")
        plt.xlabel("".join(
                   [self.name, '(', self.code, ')  ',
                    today,
                    "\n終値:",
                    '{:,d}'.format(_close),
                    ' (',
                    _close_change,
                    ', ',
                    str(_close_ratio),
                    '%)\n',
                    ' 出来高:',
                    '{:,d}'.format(_volume),
                    ' 最高:',
                    '{:,d}'.format(_stock_max),
                    ' 最安:',
                    '{:,d}'.format(_stock_min),
                    ' 分類器予測:',
                    _clf_result,
                    ' 回帰分析:',
                    '{:,d}'.format(reg_result),
                    ]),
                   fontdict={"fontproperties": self.fontprop})
        if axis >= 2:
            ncol = complexity + 3
            plt.legend(loc='upper center', bbox_to_anchor=(0.48, 1.23),
                       ncol=ncol, fancybox=False, shadow=False)
        else:
            ncol = complexity + 2
            plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.105),
                       ncol=ncol, fancybox=False, shadow=False)

        plt.savefig("".join([prefix, "_", self.code, ".png"]))
        plt.close()
