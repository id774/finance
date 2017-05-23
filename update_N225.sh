#!/bin/bash

JOBLOG=/var/log/sysadmin/stock.log
WORK_DIR=/var/stock
RUBY=/opt/ruby/current/bin/ruby
PYTHON=/opt/python/current/bin/python
STOCKTXT=$WORK_DIR/data/stocks.txt

cd $WORK_DIR/data

echo -n "*** $0: Job started on `/bin/hostname` at ">>$JOBLOG 2>&1
date "+%Y/%m/%d %T">>$JOBLOG 2>&1

$PYTHON $WORK_DIR/bin/charts.py -a 2 -p 1 -c N225 -n 日経平均株価 -d 2014-01-01 -y 600 -r stock_N225.csv -u>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/charts.py -a 2 -p 3 -c N225 -n 日経平均株価 -d 2014-01-01 -y  60 -r stock_N225.csv>>$JOBLOG 2>&1
$PYTHON $WORK_DIR/bin/charts.py -a 2 -p 2 -c N225 -n 日経平均株価 -d 2014-01-01 -y 240 -r stock_N225.csv>>$JOBLOG 2>&1

echo -n "*** $0: Job ended on `/bin/hostname` at ">>$JOBLOG 2>&1
date "+%Y/%m/%d %T">>$JOBLOG 2>&1
echo>>$JOBLOG 2>&1

exit 0
