import sys
import os
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from file_io import FileIO
import os
import pandas as pd

def testdata():
    days = 30
    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'stock_N225.csv')
    stock_tse = pd.read_csv(filename,
                            index_col=0, parse_dates=True)
    return stock_tse.asfreq('B')[days:]

def test_save_data():
    stock = testdata()
    io = FileIO()

    filename = os.path.join(os.path.dirname(
                            os.path.abspath(__file__)),
                            'test_N225.csv')

    io.save_data(stock, "N225", "test_")

    expected = True
    eq_(expected, os.path.exists(filename))

    if os.path.exists(filename):
        os.remove(filename)

if __name__ == '__main__':
    stock = testdata()
