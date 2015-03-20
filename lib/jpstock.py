# coding: utf-8

import sys
import datetime
import pandas as pd
import pandas.io.data as web

class JpStock:

    def _base_url(self):
        return ('http://info.finance.yahoo.co.jp/history/'
                '?code={0}.T&{1}&{2}&tm={3}&p={4}')

    def get(self, code, start=None, end=None, interval='d'):
        if code == 'N225':
            start = datetime.datetime.strptime(start, '%Y-%m-%d')
            result = web.DataReader('^N225', 'yahoo', start, end)

            return result.asfreq('B')

        base = self._base_url()
        start, end = web._sanitize_dates(start, end)
        start = 'sy={0}&sm={1}&sd={2}'.format(
            start.year, start.month, start.day)
        end = 'ey={0}&em={1}&ed={2}'.format(end.year, end.month, end.day)
        p = 1
        results = []

        if interval not in ['d', 'w', 'm', 'v']:
            raise ValueError(
                "Invalid interval: valid values are 'd', 'w', 'm' and 'v'")

        while True:
            url = base.format(int(code), start, end, interval, p)
            tables = pd.read_html(url, header=0)
            if len(tables) < 2 or len(tables[1]) == 0:
                break
            results.append(tables[1])
            p += 1

        result = pd.concat(results, ignore_index=True)

        result.columns = [
            'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
        result['Date'] = pd.to_datetime(result['Date'], format='%Y年%m月%d日')
        result = result.set_index('Date')
        result = result.sort_index()
        return result.asfreq('B')


if __name__ == '__main__':
    argsmin = 2
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            try:
                stock = sys.argv[1]
                start = sys.argv[2]

                jpstock = JpStock()
                stock_tse = jpstock.get(stock, start=start)
                stock_tse.to_csv("".join(["stock_", stock, ".csv"]))
            except ValueError:
                print("Value Error occured in", stock)
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
