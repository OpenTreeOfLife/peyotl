#!/bin/sh
plr="peyotl/test/output/pytlint_report"
pylint --rcfile=dev/pylintrc peyotl | tee "$plr" | sed -n '/Report/q;p'
grep '^Your code has been rated' "$plr"
./test.sh
