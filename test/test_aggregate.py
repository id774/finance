import sys
import os
from nose.tools import eq_
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p not in sys.path:
    sys.path.append(p)
from aggregate import Aggregator

def test_summarize():
    c_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(c_dir, '..')
    stock_list = os.path.join(base_dir, 'data',
                              'stocks.txt')
    data_dir = os.path.join(base_dir, 'test')
    aggregator = Aggregator(stock_list, data_dir)
    result = aggregator.summarize()

    eq_('stocks.txt', os.path.basename(aggregator.stock_list))
    eq_('test', os.path.basename(aggregator.data_dir))

    eq_(True, result.empty)
    return result

if __name__ == '__main__':
    test_summarize()
