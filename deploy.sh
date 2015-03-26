#!/bin/sh

sudo cp -av main.py /var/stock/
sudo cp -av lib /var/stock/
sudo chown -R root:adm /var/stock/
sudo chmod 750 /var/stock
sudo chmod 750 /var/stock/lib
sudo chmod 640 /var/stock/*.py
sudo chmod 640 /var/stock/lib/*.py

