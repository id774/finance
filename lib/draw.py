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

    def plot(self, stock_d, ewma, bbands, sar,
             ret, rsi, roc, mfi, ultosc,
             stoch, tr, vr,
             clf_result, axis=2):

        plotting._all_kinds.append('ohlc')
        plotting._common_kinds.append('ohlc')
        plotting._plot_klass['ohlc'] = OhlcPlot

        fig = plt.figure(figsize=(12.80, 10.24))

        if axis >= 2:
            ret['ret_index'] = ret['ret_index'] * 100
            roc['roc10'] = roc['roc10'] + 50
            tr['vl'] = tr['vl'] * 10

            ax1 = fig.add_subplot(2, 1, 1)
            ret['ret_index'].plot(label="RET",
                                  color="#888888", ax=ax1)
            rsi['rsi9'].plot(label="RSI9",
                             color="g", ax=ax1)
            rsi['rsi14'].plot(label="RSI14",
                              color="r", ax=ax1)
            roc['roc10'].plot(label="ROC",
                              color="b", ax=ax1)
            rsi['mfi14'].plot(label="MFI",
                              color="#DD88DD", ax=ax1)
            rsi['ultosc'].plot(label="UO",
                               color="m", ax=ax1)
            stoch['slowk'].plot(label="SLOWK",
                                color="y", ax=ax1)
            stoch['slowd'].plot(label="SLOWD",
                                color="k", ax=ax1)
            tr['vl'].plot(label="VL",
                          color="c", ax=ax1)
            vr['v_rate'].plot(label="VOL", kind='area',
                              color="#DDFFFF", ax=ax1)
            # stochf['fastk'].plot(label="FASTK")
            # stochf['fastd'].plot(label="FASTD")
            ax1.set_yticks([0, 25, 50, 75, 100, 125])
            plt.legend(loc='upper center', bbox_to_anchor=(0.42, 1.23),
                       ncol=5, fancybox=False, shadow=False)

            ax2 = fig.add_subplot(2, 1, 2)
        else:
            ax2 = fig.add_subplot(1, 1, 1)

        # sma['sma5'].plot(label="SMA5")
        # sma['sma25'].plot(label="SMA25")
        # sma['sma75'].plot(label="SMA75")
        ewma['ewma5'].plot(label="MA5",
                           color="k", ax=ax2)
        ewma['ewma25'].plot(label="MA25",
                            color="g", ax=ax2)
        ewma['ewma75'].plot(label="MA75",
                            color="r", ax=ax2)
        bbands['upperband'].plot(label="UPPER",
                                 color="c", ax=ax2)
        bbands['middleband'].plot(label="MIDDLE",
                                  color="m", ax=ax2)
        bbands['lowerband'].plot(label="LOWER",
                                 color="y", ax=ax2)
        sar['sar'].plot(linestyle=':', label="SAR",
                        color="#0044FF", ax=ax2)

        stock_d.plot(kind='ohlc',
                     colorup='r', colordown='b',
                     ax=ax2)

        _ret_index = round(ret.ix[-1, 'ret_index'], 2)
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
                    '%) 明日予測:',
                    _clf_result,
                    "\nリターン:",
                    str(_ret_index),
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
