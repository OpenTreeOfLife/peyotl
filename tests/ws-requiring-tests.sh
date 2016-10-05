#!/bin/bash
# This is a set of tests that use Open Tree web services (or external web services, such as TreeBASE).
# They are useful for testing peyotl's interactions with those services, but they can fail for server
#   or network reasons even if your local copy of peyotl is fine.
source tests/bash-test-helpers.bash || exit
demand_at_top_level || exit

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
