import sys
import os
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from aggregate import Aggregator

def main():
    c_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(c_dir, '..')
    data_dir = os.path.join(base_dir, 'data')
    stock_list = os.path.join(data_dir,
                              'stocks.txt')

    aggregator = Aggregator(stock_list, data_dir)
    result = aggregator.summarize()
    p = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'data',
        'summary.csv')
    result.to_csv(p, sep="\t", index_label="Code")

if __name__ == '__main__':
    argsmin = 0
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            result = main()
            if result:
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
