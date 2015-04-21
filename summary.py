import sys
import os
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from aggregate import Aggregator

def main():
    aggregator = Aggregator()
    result = aggregator.summarize()
    result.to_csv('result.csv', sep="\t")

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
