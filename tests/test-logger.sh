#!/bin/bash
for d in peyotl extras scripts tutorials tests
do
    if ! test -d "$d"
    then
        echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
        exit 1
    fi
done
unset PEYOTL_CONFIG_FILE
unset PEYOTL_LOGGING_LEVEL
unset PEYOTL_LOG_FILE_PATH
unset PEYOTL_LOGGING_FORMAT
if test -f "$HOME/.peyotl/config"
then
    echo "The $0 tests are being skipped because these tests are only runnable by developers who do not have a ~/.peyotl/config file. These tests write that file to test the configuration cascade."
    exit 0
fi
outdir=tests/output
mid=logger_test_messages
esuffix=${mid}_err.txt
osuffix=${mid}_out.txt
prefix=default
python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
prefix=debug
PEYOTL_LOGGING_LEVEL=${prefix} python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
prefix=critical
PEYOTL_LOGGING_LEVEL=${prefix} python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
