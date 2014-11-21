#!/bin/sh
plr="peyotl/test/output/pytlint_report"
echo "See http://opentreeoflife.github.io/peyotl/pylint for notes on how we use pylint"
echo "Running pylint..."
pylint --rcfile=dev/pylintrc peyotl > "$plr"
cat "$plr" | sed -n '/Report/q;p'
grep '^Your code has been rated' "$plr"
