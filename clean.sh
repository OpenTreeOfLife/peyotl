#! /bin/sh
find . -name "*.pyc" -exec rm {} \;
rm -fv peyotl/test/output/*
rm -fv peyotl/test/coverage/source/*
rm -fv peyotl/test/coverage/report/*
rm -rfv build
rm -rfv dist
rm .expected_*
rm peyotl/test/scratch/.2.*
rm peyotl/test/scratch/.1.*
rm peyotl/test/scratch/.3.*
rm peyotl/test/scratch/.clique.*
rm .obtained_*
