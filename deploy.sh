#!/bin/sh

TARGET_DIR=/var/stock
test -d $TARGET_DIR || sudo mkdir -p $TARGET_DIR
sudo cp -av bin $TARGET_DIR
sudo cp -av lib $TARGET_DIR
test -d $TARGET_DIR/clf || sudo mkdir -p $TARGET_DIR/clf
test -d $TARGET_DIR/data || sudo mkdir -p $TARGET_DIR/data
test -d $TARGET_DIR/data/history || sudo mkdir -p $TARGET_DIR/data/history
test -d $TARGET_DIR/bin/__pycache__ && sudo rm -rf $TARGET_DIR/bin/__pycache__
test -d $TARGET_DIR/lib/__pycache__ && sudo rm -rf $TARGET_DIR/lib/__pycache__
sudo cp -av run.sh $TARGET_DIR/
sudo chmod 750 $TARGET_DIR
sudo chmod 750 $TARGET_DIR/run.sh
sudo chmod 770 $TARGET_DIR/data
sudo chmod -R g+r,o-rwx $TARGET_DIR
sudo chown -R root:adm $TARGET_DIR
sudo chown root:www-data $TARGET_DIR
sudo chown -R $USER:adm $TARGET_DIR/clf
sudo chown -R $USER:www-data $TARGET_DIR/data
sudo cp -av cron.d/stock /etc/cron.d/
sudo chmod -R g+r,o-rwx /etc/cron.d/stock
sudo chown -R root:adm /etc/cron.d/stock
