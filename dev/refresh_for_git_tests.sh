#!/bin/sh
d="$(dirname $0)"
cd "$d"
cd ..
if ! test -d ./peyotl/test/data/template_mini_par
then
    echo '"peyotl/test/data/template_mini_par" does not exist! run bootstrap.sh first'
    exit 1
fi
if test -d ./peyotl/test/data/mini_par
then
    echo 'removing peyotl/test/data/mini_par tree!'
    set -x
    rm -rf ./peyotl/test/data/mini_par
fi
cp -r ./peyotl/test/data/template_mini_par ./peyotl/test/data/mini_par
