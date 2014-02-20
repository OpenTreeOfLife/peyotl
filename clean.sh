#! /bin/sh
find . -name "*.pyc" -exec rm {} \;
rm -fv peyotl/test/output/*
rm -fv peyotl/test/coverage/source/*
rm -fv peyotl/test/coverage/report/*
rm -rfv build
rm -rfv dist
rm .expected_rt*
rm peyotl/test/.2.xml
rm peyotl/test/.1.xml
rm peyotl/test/.1.json
rm .obtained_rt*
