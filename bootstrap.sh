#!/bin/sh
# Checks out mini_* repos into 
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
    git clone https://github.com/mtholder/mini_phyl.git || exit
fi
if test -d mini_system
then
    echo "mini_system exists"
else
    git clone https://github.com/mtholder/mini_system.git || exit
fi
if test -d mini_collections
then
    echo "mini_collections exists"
else
    git clone https://github.com/jimallman/mini_collections.git || exit
fi
if test -d mini_amendments
then
    echo "mini_amendments exists"
else
    git clone https://github.com/jimallman/mini_amendments.git || exit
fi
if test -d mini_illustrations
then
    echo "mini_illustrations exists"
else
    git clone https://github.com/jimallman/mini_illustrations.git || exit
fi
cd .. || exit
cp -r template_mini_par mini_par
