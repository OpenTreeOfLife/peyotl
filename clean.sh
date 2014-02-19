#! /bin/sh
find . -name "*.pyc" -exec rm {} \;
rm -fv peyotl/test/output/*
rm -fv peyotl/test/coverage/source/*
rm -fv peyotl/test/coverage/report/*
rm -rfv build
rm -rfv dist
