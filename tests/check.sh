#!/bin/sh
for d in peyotl extras scripts tutorials tests
do 
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
./dev/run_pylint.sh
f=0
echo "Running integration-tests.sh ..."
if ! ./tests/integration-tests.sh
then
    f=1
fi
echo "Running uniitests..."
if ! python setup.py test
then
    f=1
fi
exit $f

