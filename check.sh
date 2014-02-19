#!/bin/sh
plr="peyotl/test/output/pytlint_report"
echo "Running pylint..."
pylint --rcfile=dev/pylintrc peyotl | tee "$plr" | sed -n '/Report/q;p'
grep '^Your code has been rated' "$plr"
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

