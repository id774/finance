#!/bin/bash

JOBLOG=/var/log/sysadmin/stock.log
WORK_DIR=/var/stock
RUBY=/opt/ruby/current/bin/ruby
PYTHON=/opt/python/current/bin/python
STOCKTXT=$WORK_DIR/stocks.txt
STARTDATE=2015-01-01
DAYS=90

cd $WORK_DIR/data

$PYTHON $WORK_DIR/main.py -s $STOCKTXT -d $STARTDATE -y $DAYS>$JOBLOG 2>&1
