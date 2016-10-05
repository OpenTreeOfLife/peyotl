#!/bin/bash
# This is a set of tests that use Open Tree web services (or external web services, such as TreeBASE).
# They are useful for testing peyotl's interactions with those services, but they can fail for server
#   or network reasons even if your local copy of peyotl is fine.

for d in peyotl extras scripts tutorials tests
do 
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
stf=0
bash tests/tutorial-tests.sh
lpstf="$?"
stf=$(expr ${stf} + ${lpstf})
if test ${stf} -gt 0
then
    echo "Failed at least one $0 test."
    exit ${stf}
else
    echo "Passed all $0 tests passed."
fi
