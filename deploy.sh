#!/bin/sh

TARGET_DIR=/var/stock
test -d $TARGET_DIR || sudo mkdir -p $TARGET_DIR
sudo cp -av charts.py $TARGET_DIR
sudo cp -av lib $TARGET_DIR
sudo chmod 750 $TARGET_DIR
test -d $TARGET_DIR/data || sudo mkdir -p $TARGET_DIR/data
sudo cp -av run.sh $TARGET_DIR/
sudo chmod 750 $TARGET_DIR/run.sh
sudo chown -R root:adm $TARGET_DIR
sudo chown -R $USER:adm $TARGET_DIR/stocks.txt
sudo chown -R $USER:adm $TARGET_DIR/data
