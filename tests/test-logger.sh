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

prefixarray=(toslashtmp default debug critical fdefault)
for prefix in ${prefixarray[@]}
do
    for suffix in ${esuffix} ${osuffix}
    do
        ff="${outdir}/${prefix}_${suffix}"
        if test -f "$ff"
        then
            echo "  cleaning up ${ff}" ; rm "$ff" || exit
        fi
     done
done

num_fails=0
num_checks=0
function demand_empty {
    for f in $@
    do
        num_checks=$(expr 1 + ${num_checks})
        if test -s ${f}
        then
            echo "File \"$f\" was not empty, but should have been!"
            num_fails=$(expr 1 + ${num_fails})
        fi
    done
}

function demand_str_found {
    f=$1
    shift
    for s in $@
    do
        num_checks=$(expr 1 + ${num_checks})
        if ! grep "${s}" "${f}" >/dev/null
        then
            echo "File \"${f}\" should have (but did not) match \"${s}\""
            num_fails=$(expr 1 + ${num_fails})
        fi
    done
}

function demand_str_not_found {
    f=$1
    shift
    for s in $@
    do
        num_checks=$(expr 1 + ${num_checks})
        if grep "${s}" "${f}" >/dev/null
        then
            echo "File \"${f}\" should matched \"${s}\" but should not have"
            num_fails=$(expr 1 + ${num_fails})
        fi
    done
}

function files_are_identical {
    f=$1
    shift
    for s in $@
    do
        num_checks=$(expr 1 + ${num_checks})
        if ! diff "${s}" "${f}" >/dev/null
        then
            echo "File \"${f}\" and \"${s}\" differed"
            num_fails=$(expr 1 + ${num_fails})
        fi
    done

}

# The default config comes from $PEYOTL_ROOT/peyotl.conf
#   level = info
#   filepath = /tmp/peyotl-log
#   formatter = simple

# default run should write to /tmp/peyotl-log. We won't verify that in case tests are running multithreaded. Just check that stderr is empty.
prefix=toslashtmp
python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
demand_empty ${outdir}/${prefix}_${esuffix}

# an empty string PEYOTL_LOG_FILE_PATH causes writing to stderr
export PEYOTL_LOG_FILE_PATH=''
prefix=default
python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
demand_str_found "${outdir}/${prefix}_${esuffix}" info warning error critical exception
demand_str_not_found "${outdir}/${prefix}_${esuffix}" debug

prefix=debug
PEYOTL_LOGGING_LEVEL=${prefix} python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
demand_str_found "${outdir}/${prefix}_${esuffix}" debug info warning error critical exception

prefix=critical
PEYOTL_LOGGING_LEVEL=${prefix} python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
demand_str_found "${outdir}/${prefix}_${esuffix}" critical
demand_str_not_found "${outdir}/${prefix}_${esuffix}" debug info warning error exception


prefix=fdefault
export PEYOTL_LOG_FILE_PATH="${outdir}/${prefix}_${esuffix}"
python tests/logger_test_messages.py 2>${outdir}/${prefix}_${esuffix} >${outdir}/${prefix}_${osuffix}
files_are_identical ${outdir}/${prefix}_${esuffix} ${outdir}/default_${esuffix}


# all of the output stream should be empty
for prefix in  ${prefixarray[@]}
do
    demand_empty "${outdir}/${prefix}_${osuffix}"
done


num_passes=$(expr ${num_checks} - ${num_fails})
echo "Passed $num_passes out of $num_checks checks"
test ${num_checks} = ${num_passes}