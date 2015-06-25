import sys
import os
import datetime
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

    def __init__(self, code, name, **kwargs):
        self.code = code
        self.name = name
        if sys.platform == "darwin":
            font_path = "/Library/Fonts/Osaka.ttf"
        else:
            font_path = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
        self.fontprop = font_manager.FontProperties(
            fname=font_path)
        self.ref_result = ""

    def plot(self, stock_d, ewma, bbands, sar,
             rsi, roc, mfi, ultosc, willr,
             stoch, tr, vr,
             clf_result, ref=[], axis=2):

        plotting._all_kinds.append('ohlc')
        plotting._common_kinds.append('ohlc')
        plotting._plot_klass['ohlc'] = OhlcPlot

        fig = plt.figure(figsize=(12.80, 10.24))

        if axis >= 2:
            roc['roc10'] = roc['roc10'] + 50
            roc['roc25'] = roc['roc25'] + 50
            willr['willr14'] = willr['willr14'] + 100
            tr['vl'] = tr['vl'] * 5

            ax1 = fig.add_subplot(2, 1, 1)
            rsi['rsi9'].plot(label="RSI9",
                             color="g", ax=ax1)
            rsi['rsi14'].plot(label="RSI14",
                              color="r", ax=ax1)
            roc['roc10'].plot(label="ROC10",
                              color="b", ax=ax1)
            roc['roc25'].plot(label="ROC25",
                              color="#888888", ax=ax1)
            mfi['mfi14'].plot(label="MFI",
                              color="#DD88DD", ax=ax1)
            ultosc['ultosc'].plot(label="UO",
                                  color="m", ax=ax1)
            stoch['slowk'].plot(label="SLOWK",
                                color="y", ax=ax1)
            stoch['slowd'].plot(label="SLOWD",
                                color="k", ax=ax1)
            willr['willr14'].plot(linestyle=':', label="%R",
                                  color="#FF0088", ax=ax1)
            tr['vl'].plot(label="VL",
                          color="c", ax=ax1)
            vr['v_rate'].plot(label="VOL", kind='area',
                              color="#DDFFFF", ax=ax1)
            if len(ref) > 0:
                self.ref_result = (" 日経平均相関:" +
                                   str(round(ref.mean(), 2)))
                ref = ref * 50 + 50
                ref.plot(linestyle=':', label="REF",
                         color="#DDDDDD", ax=ax1)
            ax1.set_yticks([0, 25, 50, 75, 100])
            plt.legend(loc='upper center', bbox_to_anchor=(0.48, 1.23),
                       ncol=6, fancybox=False, shadow=False)

            ax2 = fig.add_subplot(2, 1, 2)
        else:
            ax2 = fig.add_subplot(1, 1, 1)

        ewma['ewma5'].plot(label="MA5",
                           color="k", ax=ax2)
        ewma['ewma25'].plot(label="MA25",
                            color="g", ax=ax2)
        ewma['ewma50'].plot(label="MA50",
                            color="m", ax=ax2)
        ewma['ewma75'].plot(label="MA75",
                            color="r", ax=ax2)
        bbands['upperband'].plot(label="UPPER",
                                 color="c", ax=ax2)
        bbands['lowerband'].plot(label="LOWER",
                                 color="y", ax=ax2)
        sar['sar'].plot(linestyle=':', label="SAR",
                        color="#00FF88", ax=ax2)

        stock_d.plot(kind='ohlc',
                     colorup='r', colordown='b',
                     ax=ax2)

        _volume = int(stock_d.ix[-1, 'Volume'])
        _open = int(stock_d.ix[-1, 'Open'])
        _high = int(stock_d.ix[-1, 'High'])
        _low = int(stock_d.ix[-1, 'Low'])
        _close = int(stock_d.ix[-1, 'Adj Close'])
        _last_close = int(stock_d.ix[-2, 'Adj Close'])
        _stock_max = int(stock_d.ix[:, 'High'].max())
        _stock_min = int(stock_d.ix[:, 'Low'].min())
        _close_diff = _close - _last_close
        _close_ratio = round((1 + _close_diff) / _close * 100, 2)
        if _close_diff >= 0:
            _close_diff = "".join(['+', str(_close_diff)])
        else:
            _close_diff = str(_close_diff)
        if clf_result == 0:
            _clf_result = "↓"
        else:
            _clf_result = "↑"

        today = datetime.datetime.today().strftime("%a %d %b %Y")
        plt.xlabel("".join(
                   [self.name, '(', self.code, ') ',
                    today,
                    "\n始:",
                    '{:,d}'.format(_open),
                    ' 高:',
                    '{:,d}'.format(_high),
                    ' 安:',
                    '{:,d}'.format(_low),
                    ' 終:',
                    '{:,d}'.format(_close),
                    ' (',
                    _close_diff,
                    ', ',
                    str(_close_ratio),
                    '%)',
                    self.ref_result,
                    "\n明日予測:",
                    _clf_result,
                    ' 出来高:',
                    '{:,d}'.format(_volume),
                    ' 最高:',
                    '{:,d}'.format(_stock_max),
                    ' 最安:',
                    '{:,d}'.format(_stock_min),
                    ' 前終:',
                    '{:,d}'.format(_last_close),
                    ]),
                   fontdict={"fontproperties": self.fontprop})
        plt.legend(loc='upper center', bbox_to_anchor=(0.367, 1.228),
                   ncol=4, fancybox=False, shadow=False)
        plt.savefig("".join(["chart_", self.code, ".png"]))
        plt.close()
