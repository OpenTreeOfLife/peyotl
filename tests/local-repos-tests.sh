#!/bin/sh
for d in peyotl extras scripts tutorials tests
do 
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
stf=0
bash tests/local-phylesystem-tests.sh
lpstf="$?"
stf=$(expr ${stf} + ${lpstf})
if test ${stf} -gt 0
then
    echo "Failed at least one local-repo.sh test."
    exit ${stf}
else
    echo "Passed all local-repo.sh tests passed."
fi
