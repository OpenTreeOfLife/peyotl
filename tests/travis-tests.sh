#!/bin/bash
# On Travis we avoid tests that use the web services, and tests that require the local phylesystem
for d in peyotl extras scripts tutorials tests
do 
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
num_fails=0
if ! bash tests/test-logger.sh
then
    num_fails=$(expr 1 + ${num_fails})
fi
f=0
if ! ./tests/integration-tests.sh
then
    f=1
fi
s=0
if ! python setup.py test
then
    s=1
fi
if test ${num_fails} -eq 0
then
    echo "Passed all test-logger.sh script tests."
else
    echo "Failed at least one test-logger.sh script tests."
fi
if test ${f} -eq 0
then
    echo "Passed all integration-tests.sh tests."
else
    echo "Failed at least one integration-tests.sh script tests."
fi
exit $(expr ${f} + ${s} + ${num_fails})

