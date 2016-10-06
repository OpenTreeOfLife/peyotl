#!/bin/sh
# This is a helper script used by the $PEYOTL_ROOT/tests/local-phylesystem-tests.sh
#   It does a recursive rm of:
#       ${PEYOTL_ROOT}/peyotl/test/data/mini_par
#   tree of testing repos, and replaces them with a fresh copy of the files in
#       ${PEYOTL_ROOT}/peyotl/test/data/template_mini_par
# So that one test corrupting the repos wont cause all subsequent tests to fail
for d in dev peyotl extras scripts tutorials tests
do
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
if ! test -d ./peyotl/test/data/template_mini_par
then
    echo '"peyotl/test/data/template_mini_par" does not exist! run bootstrap.sh first'
    exit 1
fi
if test -d ./peyotl/test/data/mini_par
then
    rm -rf ./peyotl/test/data/mini_par
fi
cp -r ./peyotl/test/data/template_mini_par ./peyotl/test/data/mini_par
