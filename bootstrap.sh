#!/bin/sh
# Checks out mini_phyl and mini_system repos into 
#   peyotl/test/data/template_mini_par
d="$(dirname $0)"
cd "$d"
if test -d peyotl/test/data/template_mini_par
then
    echo peyotl/test/data/template_mini_par exists
    exit 1
fi
set -x
mkdir peyotl/test/data/template_mini_par || exit
cd peyotl/test/data/template_mini_par || exit
if test -d mini_phyl
then
    echo "mini_phyl exists"
else
    git clone https://github.com/snacktavish/mini_phyl.git || exit
fi
if test -d mini_system
then
    echo "mini_system exists"
else
    git clone https://github.com/snacktavish/mini_system.git || exit
fi
