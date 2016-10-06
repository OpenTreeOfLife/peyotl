#!/bin/sh
for d in peyotl extras scripts tutorials tests
do 
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
set -x
ttf=0
if ! python tutorials/ot-tnrs-match-names.py Hominidae >tutorials/tutorial-test-output 2>tutorials/tutorial-test-err-output
then
    ttf=$(expr $ttf + 1)
    cat tutorials/tutorial-test-err-output
fi
if ! python tutorials/ot-taxon-info.py 770311 >tutorials/tutorial-test-output 2>tutorials/tutorial-test-err-output
then
    ttf=$(expr $ttf + 1)
    cat tutorials/tutorial-test-err-output
fi

if ! python tutorials/ot-oti-find-tree.py '{"ot:ottId": 84761}' >tutorials/tutorial-test-output 2>tutorials/tutorial-test-err-output
then
    ttf=$(expr $ttf + 1)
    cat tutorials/tutorial-test-err-output
fi
if ! python tutorials/ot-tree-of-life-mrca.py 770311 >tutorials/tutorial-test-output 2>tutorials/tutorial-test-err-output
then
    ttf=$(expr $ttf + 1)
    cat tutorials/tutorial-test-err-output
fi

if test $ttf -gt 0
then
    echo "Failed at least one tutorial test"
    exit $ttf
else
    echo "Passed all tutorial tests passed."
fi
