#!/bin/sh
stt=0
stf=0
for f in $(ls standalone_tests/test*py)
do 
    stt=$(expr $stt + 1)
    ./dev/refresh_for_git_tests.sh
    if ! python $f
    then
        stf=$(expr $stf + 1)
    fi
done
if test $stf -gt 0
then
    echo "Passed all standalone_tests passed."
else
    echo "Failed at least one standalone_test."
    exit $stf
fi
