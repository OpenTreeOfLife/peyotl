#!/bin/sh
#set -x
f=0
r=0 # the number of tests
if ! ./integration-tests.sh
then
    f=1
    r=1
fi

if ! python setup.py test
then
    f=1
fi

if test $r -eq 0
then
    echo "Passed all shell script tests."
else
    echo "Failed at least one shell script tests."
fi
exit $f