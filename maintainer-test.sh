#!/bin/sh
#set -x
f=0 # the number of tests
if ! ./integration-tests.sh
then
    f=1
fi
k=0
if ! ./standalone-tests.sh
then
    k=1
fi
s=0
if ! python setup.py test
then
    s=1
fi

if test $f -eq 0
then
    echo "Passed all shell script tests."
else
    echo "Failed at least one shell script tests."
fi
if test $k -eq 0
then
    echo "Passed all standalone_tests passed."
else
    echo "Failed at least one standalone_test."
fi
exit $(expr $f + $k + $s)