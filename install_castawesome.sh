#! /bin/sh

mkdir -p /usr/local/share/castawesome/ui
mkdir -p /usr/local/share/castawesome/doc
cp *.ui /usr/local/share/castawesome/ui
cp README AUTHORS NEWS COPYING /usr/local/share/castawesome/doc
cp castawesome.py /usr/local/bin/castawesome
cp uninstall_castawesome.sh /usr/local/bin/uninstall_castawesome
cp Castawesome.desktop /usr/local/share/applications
