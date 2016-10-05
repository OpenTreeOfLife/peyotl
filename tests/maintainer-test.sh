#!/bin/bash
# A new version of the harness for running the full set of tests of peyotl including tests that are a pain to set up.
# will become maintainer-test.sh when it is full working.
for d in peyotl extras scripts tutorials tests
do 
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
num_fails=0
num_checks=1
if ! bash tests/test-logger.sh
then
    num_fails=$(expr 1 + ${num_fails})
fi
f=0
if ! ./tests/integration-tests.sh
then
    f=1
fi
k=0
if ! ./tests/local-repos-tests.sh
then
    k=1
fi
t=0
if ! ./tests/ws-requiring-tests.sh
then
    t=1
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
if test ${k} -eq 0
then
    echo "Passed all local-repo-tests.sh test."
else
    echo "Failed at least one local-repo-tests.sh test."
fi
if test ${t} -eq 0
then
    echo "Passed all ws-requiring tests."
else
    echo "Failed at least one ws-requiring test"
fi
exit $(expr ${f} + ${k} + ${s} + ${t} + ${num_fails})

