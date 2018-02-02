#!/bin/bash

JOBLOG=/var/log/sysadmin/stock.log
WORK_DIR=/var/stock
RUBY=/opt/ruby/current/bin/ruby
PYTHON=/opt/python/current/bin/python
STOCKTXT=$WORK_DIR/data/stocks.txt
STARTDATE=2014-10-01
DAYS=240
LONGDAYS=600
SHORTDAYS=60

cd $WORK_DIR/data

echo -n "*** $0: Job started on `/bin/hostname` at ">>$JOBLOG 2>&1
date "+%Y/%m/%d %T">>$JOBLOG 2>&1

$PYTHON $WORK_DIR/bin/charts.py -a 2 -p 2 -s $STOCKTXT -d $STARTDATE -y $DAYS -u>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -o summary.csv -y -r 1 -k Ratio>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -o summary_10.csv -r 10 -k Ratio>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -s my_stocks.txt -o portfolio.csv -r 1 -k Ratio>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -s topix_core30.txt -o topix_core30.csv -r 1 -c rsi9 -k Ratio>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/summary.py -o screening_rsi14.csv -r 1 -c rsi14 -a -k rsi14>>$JOBLOG 2>&1
$RUBY $WORK_DIR/bin/email.rb>>$JOBLOG 2>&1
# $RUBY $WORK_DIR/bin/email.rb "rolling_corr.csv" "Summary Report sorted by corr">>$JOBLOG 2>&1
$RUBY $WORK_DIR/bin/email.rb "portfolio.csv" "Summary Report of My Portfolio">>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/charts.py -a 2 -p 1 -s $STOCKTXT -d $STARTDATE -y $LONGDAYS>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/charts.py -a 2 -p 3 -s $STOCKTXT -d $STARTDATE -y $SHORTDAYS>>$JOBLOG 2>&1

echo -n "*** $0: Job ended on `/bin/hostname` at ">>$JOBLOG 2>&1
date "+%Y/%m/%d %T">>$JOBLOG 2>&1
echo>>$JOBLOG 2>&1

exit 0
