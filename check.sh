#!/bin/sh
./dev/run_pylint.sh
f=0
echo "Running integration-tests.sh ..."
if ! ./integration-tests.sh
then
    f=1
fi
echo "Running uniitests..."
if ! python setup.py test
then
    f=1
fi
exit $f

