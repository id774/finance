import sys
import os
import pandas as pd
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'lib')
if p in sys.path:
    pass
else:
    sys.path.append(p)
from analysis import Analysis

def read_csv(filename, start, days):
    stocks = pd.read_csv(filename, header=True)
    for s in stocks.values:
        analysis = Analysis(stock=str(s[0]),
                            name=s[1],
                            start=start,
                            days=days)
        analysis.run()

def main():
    from optparse import OptionParser
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-c", "--code", dest="stockcode",
                      help="stock code")
    parser.add_option("-n", "--name", dest="stockname",
                      help="stock name")
    parser.add_option("-s", "--stock", dest="stocktxt",
                      help="read scraping stock names from text file")
    parser.add_option("-r", "--readfile", dest="csvfile",
                      help="read stock data from csv file")
    parser.add_option("-d", "--date", dest="startdate",
                      help="specify start date as '2014-09-01'")
    parser.add_option("-y", "--days", dest="days",
                      help="plot days as '-90', specify 0 for all days")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.error("incorrect number of arguments")

    if options.stocktxt:
        read_csv(filename=options.stocktxt,
                 start=options.startdate,
                 days=options.days)
    else:
        analysis = Analysis(stock=options.stockcode,
                            name=options.stockname,
                            start=options.startdate,
                            days=options.days,
                            filename=options.csvfile)
        analysis.run()

if __name__ == '__main__':
    argsmin = 0
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            main()
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
