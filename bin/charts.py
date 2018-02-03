import sys
import os
import pandas as pd
p = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'lib')
if p not in sys.path:
    sys.path.append(p)
from analysis import Analysis

def read_csv(filename, start, days, update, axis, complexity):
    stocks = pd.read_csv(filename, header=None)
    for s in stocks.values:
        code = str(s[0])
        analysis = Analysis(code=code,
                            name=s[1],
                            fullname=s[2],
                            start=start,
                            days=int(days),
                            csvfile="".join(['stock_', str(s[0]), '.csv']),
                            update=True,
                            axis=int(axis),
                            complexity=int(complexity))
        result = analysis.run()
    return result

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
    parser.add_option("-u", "--update",
                      help="update csvfile (overwirte)",
                      action="store_true", dest="update")
    parser.add_option("-d", "--date", dest="startdate",
                      help="specify start date as '2014-10-01'")
    parser.add_option("-y", "--days", dest="days",
                      help="plot days as '240', specify 0 for all days")
    parser.add_option("-a", "--axis", dest="axis",
                      help="setting y-axis limit (1 or 2, default 2)")
    parser.add_option("-p", "--complexity", dest="complexity",
                      help="complexity of chart (1-3, default 3)")
    (options, args) = parser.parse_args()

    if len(args) != 0:
        parser.error("incorrect number of arguments")

    if options.days is None:
        options.days = 240

    if options.axis is None:
        options.axis = 2

    if options.complexity is None:
        options.complexity = 3

    if options.stocktxt:
        return read_csv(filename=options.stocktxt,
                        start=options.startdate,
                        days=int(options.days),
                        update=options.update,
                        axis=int(options.axis),
                        complexity=int(options.complexity))
    else:
        analysis = Analysis(code=options.stockcode,
                            name=options.stockname,
                            fullname=options.stockname,
                            start=options.startdate,
                            days=int(options.days),
                            csvfile=options.csvfile,
                            update=options.update,
                            axis=int(options.axis),
                            complexity=int(options.complexity))
        return analysis.run()

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
