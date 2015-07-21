import sys
import os
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from aggregate import Aggregator

class Summary():

    def __init__(self, filename='stocks.txt', **kwargs):
        self.c_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.join(self.c_dir, '..')
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.stock_list = os.path.join(self.data_dir,
                                       filename)
        self.aggregator = Aggregator(self.stock_list, self.data_dir)

    def aggregate(self,
                  filename,
                  range=1,
                  sortkey='Ratio',
                  ascending=False):
        result = self.aggregator.summarize(range=range,
                                           sortkey=sortkey,
                                           ascending=ascending)
        p = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'data',
            filename)
        result.to_csv(p, sep="\t", index_label="Code")

def main():
    from optparse import OptionParser
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-s", "--stock", dest="stocktxt",
                      help="read scraping stock names from text file")
    parser.add_option("-o", "--output", dest="output",
                      help="output file name")
    parser.add_option("-r", "--range", dest="range",
                      help="range for summary")
    parser.add_option("-k", "--sortkey", dest="sortkey",
                      help="sort key")
    (options, args) = parser.parse_args()

    if len(args) != 0:
        parser.error("incorrect number of arguments")

    if options.stocktxt:
        summary = Summary(filename=options.stocktxt)
    else:
        summary = Summary()

    summary.aggregate(options.output,
                      range=int(options.range),
                      sortkey=options.sortkey)

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
