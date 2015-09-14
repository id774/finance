#!/bin/bash

JOBLOG=/var/log/sysadmin/stock.log
WORK_DIR=/var/stock
RUBY=/opt/ruby/current/bin/ruby
PYTHON=/opt/python/current/bin/python
STOCKTXT=$WORK_DIR/data/stocks.txt
STARTDATE=2014-10-01
DAYS=240

cd $WORK_DIR/data

echo -n "*** $0: Job started on `/bin/hostname` at ">>$JOBLOG 2>&1
date "+%Y/%m/%d %T">>$JOBLOG 2>&1

$PYTHON $WORK_DIR/bin/charts.py -a 2 -p 3 -s $STOCKTXT -d $STARTDATE -y $DAYS -u>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -o summary.csv -y -r 1 -k Ratio>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -o summary_10.csv -r 10 -k Ratio>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -o summary_25.csv -r 25 -k Ratio>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -o rolling_corr.csv -r 1 -k Corr>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -s my_stocks.txt -o portfolio.csv -r 1 -k Ratio>>$JOBLOG 2>&1
$RUBY $WORK_DIR/bin/reference.rb>>$JOBLOG 2>&1
$RUBY $WORK_DIR/bin/email.rb>>$JOBLOG 2>&1
$RUBY $WORK_DIR/bin/email.rb "rolling_corr.csv" "Summary Report sorted by corr">>$JOBLOG 2>&1
$RUBY $WORK_DIR/bin/email.rb "portfolio.csv" "Summary Report of your Portfolio">>$JOBLOG 2>&1

echo -n "*** $0: Job ended on `/bin/hostname` at ">>$JOBLOG 2>&1
date "+%Y/%m/%d %T">>$JOBLOG 2>&1
echo>>$JOBLOG 2>&1

exit 0
