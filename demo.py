import sys
import os
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from analysis import Analysis

def demo(stock='N225',
         name='日経平均株価',
         start='2014-01-01',
         days=120,
         csvfile=os.path.join(os.path.dirname(
             os.path.abspath(__file__)),
             'test',
             'stock_N225.csv'),
         update=False):

    analysis = Analysis(stock=stock,
                        name=name,
                        start=start,
                        days=days,
                        csvfile=csvfile,
                        update=True)
    return analysis.run()
