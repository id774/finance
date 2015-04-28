#!/bin/sh

TARGET_DIR=/var/stock
test -d $TARGET_DIR || sudo mkdir -p $TARGET_DIR
sudo cp -av bin $TARGET_DIR
sudo cp -av lib $TARGET_DIR
test -d $TARGET_DIR/clf || sudo mkdir -p $TARGET_DIR/clf
test -d $TARGET_DIR/data || sudo mkdir -p $TARGET_DIR/data
sudo cp -av run.sh $TARGET_DIR/
sudo chmod 750 $TARGET_DIR
sudo chmod 750 $TARGET_DIR/run.sh
sudo chmod -R g+r,o-rwx $TARGET_DIR
sudo chown -R root:adm $TARGET_DIR
sudo chown root:www-data $TARGET_DIR
sudo chown -R $USER:adm $TARGET_DIR/stocks.txt
sudo chown -R $USER:adm $TARGET_DIR/clf
sudo chown -R www-data:www-data $TARGET_DIR/data
