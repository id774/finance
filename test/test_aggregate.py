import sys
import os
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from aggregate import Aggregator

def test_summarize():
    c_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(c_dir, '..')
    stock_list = os.path.join(base_dir,
                              'stocks.txt')
    data_dir = os.path.join(base_dir, 'test')
    aggregator = Aggregator(stock_list, data_dir)
    result = aggregator.summarize()

    expected = 19560
    eq_(expected, result.ix[-1, 'Close'])
    expected = 84
    eq_(expected, result.ix[-1, 'Diff'])
    expected = 0.43
    eq_(expected, result.ix[-1, 'Ratio'])

    return result

if __name__ == '__main__':
    test_summarize()
