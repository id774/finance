import sys
import os
import pandas as pd
from scipy import stats

def calc_zscore(df, name):
    evaluated = 300

    try:
        df = df.tail(evaluated)
        df[6] = stats.zscore(df.ix[:, 2])
    except TypeError:
        print("TypeError: " + name)
    return df

def calc_results(df, name):
    samples = 100

    trading_results = (df.tail(samples).ix[:, 6].sum()) / samples
    print(name, trading_results)

def parse_file(filename):
    try:
        df = pd.read_csv(filename, index_col=0)
        scored_df = calc_zscore(df, filename)
        calc_results(scored_df, filename)
    except pd.parser.CParserError:
        print("ParseError: " + filename)

def list_files(path):
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.endswith(".csv"):
                fullname = os.path.join(root, filename)
                parse_file(fullname)

def main(args):
    path = args[1]
    list_files(path)

if __name__ == '__main__':
    argsmin = 1
    version = (3, 0)
    if sys.version_info > (version):
        if len(sys.argv) > argsmin:
            sys.exit(main(sys.argv))
        else:
            print("This program needs at least %(argsmin)s arguments" %
                  locals())
    else:
        print("This program requires python > %(version)s" % locals())
