#! /bin/sh
d=$(dirname "$0")
if ! test -d $d
then
    echo "$d is not a directory"
    exit 1
fi
cd "$d"
find . -name "*.pyc" -exec rm {} \;
rm -fv peyotl/test/output/*
rm -fv peyotl/test/coverage/source/*
rm -fv peyotl/test/coverage/report/*
rm -rfv build
rm -rfv dist
rm -f peyotl/test/scratch/.2.*
rm -f peyotl/test/scratch/.1.*
rm -f peyotl/test/scratch/.3.*
rm -f peyotl/test/scratch/.obtained_*
rm -f peyotl/test/scratch/.expected_*
rm -f peyotl/test/scratch/.clique.*
rm -f peyotl/test/data/nexson/*/*.output
rm -f peyotl/test/data/nexson/*/*.orig
rm -f scratch/.2.*
rm -f scratch/.1.*
rm -f scratch/.3.*
rm -f scratch/.obtained_*
rm -f scratch/.expected_*
cd - >/dev/null