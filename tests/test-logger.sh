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
outdir=tests/output/logger_test
if ! test -d ${outdir}
then
    mkdir -p ${outdir}
fi
esuffix=err.txt
osuffix=out.txt

prefixarray=(toslashtmp default debug critical fdefault cdefault richdebug rawdebug boguslevel bogusformat seconddefault homeoverride)
for prefix in ${prefixarray[@]}
do
    for suffix in ${esuffix} ${osuffix}
    do
        ff="${outdir}/${prefix}_${suffix}"
        if test -f "$ff"
        then
            rm "$ff" || exit
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


function matches_formatter {
    f=$1
    shift
    for s in $@
    do
        num_checks=$(expr 1 + ${num_checks})
        if ! python tests/match_logger_output.py $f $s
        then
            echo "Format of messages in \"${s}\" was wrong"
            num_fails=$(expr 1 + ${num_fails})
        fi
    done
}

# The default config comes from $PEYOTL_ROOT/peyotl.conf
#   level = info
#   filepath = /tmp/peyotl-log
#   formatter = simple

# default run should write to /tmp/peyotl-log. We won't verify that in case tests are running multithreaded. Just check that stderr is empty.
prefix=toslashtmp ; elogf="${outdir}/${prefix}_${esuffix}"
python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_empty ${elogf}

# Check that empty string PEYOTL_LOG_FILE_PATH causes writing to stderr
export PEYOTL_LOG_FILE_PATH=''
prefix=default ; elogf="${outdir}/${prefix}_${esuffix}"
python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_str_found ${elogf} info warning error critical exception
demand_str_not_found "${elogf}" debug
matches_formatter simple ${elogf}

# Check debug run level via env
prefix=debug ; elogf="${outdir}/${prefix}_${esuffix}"
PEYOTL_LOGGING_LEVEL=${prefix} python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_str_found "${elogf}" debug info warning error critical exception
matches_formatter simple ${elogf}

# Check rich message formatter via env
prefix=richdebug ; elogf="${outdir}/${prefix}_${esuffix}"
PEYOTL_LOGGING_LEVEL=debug  PEYOTL_LOGGING_FORMAT=rich python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_str_found "${elogf}" debug info warning error critical exception
matches_formatter rich ${elogf}

# raw and debug via env
prefix=rawdebug ; elogf="${outdir}/${prefix}_${esuffix}"
PEYOTL_LOGGING_LEVEL=debug  PEYOTL_LOGGING_FORMAT=raw python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_str_found "${elogf}" debug info warning error critical exception
matches_formatter raw ${elogf}

# critical logger level via env
prefix=critical ; elogf="${outdir}/${prefix}_${esuffix}"
PEYOTL_LOGGING_LEVEL=${prefix} python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_str_found "${elogf}" critical
demand_str_not_found "${elogf}" debug info warning error exception
matches_formatter simple ${elogf}

# Log file path via env, rather than stderr redirection
prefix=fdefault ; elogf="${outdir}/${prefix}_${esuffix}"
export PEYOTL_LOG_FILE_PATH="${elogf}"
python tests/logger_test_messages.py >${outdir}/${prefix}_${osuffix}
files_are_identical ${elogf} ${outdir}/default_${esuffix}
matches_formatter simple ${elogf}

# Write a config file and verify that PEYOTL_CONFIG_FILE env variable works
prefix=cdefault ; elogf="${outdir}/${prefix}_${esuffix}"
cat >"${outdir}/logtest.conf" <<TESTLOGCONTENT
[logging]
filepath = $PWD/${elogf}
level = debug
formatter = raw
TESTLOGCONTENT
unset PEYOTL_LOG_FILE_PATH
PEYOTL_CONFIG_FILE=$PWD/${outdir}/logtest.conf python tests/logger_test_messages.py >${outdir}/${prefix}_${osuffix}
files_are_identical ${elogf} ${outdir}/rawdebug_${esuffix}


# make sure that we get the same default log before we move to ~/.peyotl/config This is really a test that
#   we haven't accidentally modified the env at this point in this test script
prefix=seconddefault ; elogf="${outdir}/${prefix}_${esuffix}"
export PEYOTL_LOG_FILE_PATH=''
python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
files_are_identical ${elogf} ${outdir}/default_${esuffix}

# Now we test the default usage of ~/.peyotl/config
if ! test -d ~/.peyotl
then
    mkdir ~/.peyotl || exit
fi
prefix=homeoverride ; elogf="${outdir}/${prefix}_${esuffix}"
cat >"$HOME/.peyotl/config" <<TESTLOGCONTENT
[logging]
filepath = $PWD/${elogf}
level = debug
formatter = simple
TESTLOGCONTENT
unset PEYOTL_LOG_FILE_PATH
python tests/logger_test_messages.py >${outdir}/${prefix}_${osuffix}
files_are_identical ${elogf} ${outdir}/debug_${esuffix}

# Make sure that PEYOTL_CONFIG_FILE env overrides the existence of ~/.peyotl/config
prefix=cdefault ; elogf="${outdir}/${prefix}_${esuffix}"
rm -f ${elogf} # we will regenerate this
PEYOTL_CONFIG_FILE=$PWD/${outdir}/logtest.conf python tests/logger_test_messages.py >${outdir}/${prefix}_${osuffix}
files_are_identical ${elogf} ${outdir}/rawdebug_${esuffix}

# clean up the config file that we just wrote
rm ~/.peyotl/config


# If we set an incorrect level, we should get a message
prefix=boguslevel ; elogf="${outdir}/${prefix}_${esuffix}"
export PEYOTL_LOG_FILE_PATH=''
PEYOTL_LOGGING_LEVEL=bogus python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_str_found ${elogf} invalid bogus

# If we set an incorrect level, we should get a message
prefix=bogusformat ; elogf="${outdir}/${prefix}_${esuffix}"
export PEYOTL_LOG_FILE_PATH=''
PEYOTL_LOGGING_FORMAT=BOGUS python tests/logger_test_messages.py 2>${elogf} >${outdir}/${prefix}_${osuffix}
demand_str_found ${elogf} invalid BOGUS


# all of the output stream should be empty
for prefix in  ${prefixarray[@]}
do
    demand_empty "${outdir}/${prefix}_${osuffix}"
done


num_passes=$(expr ${num_checks} - ${num_fails})
echo "Passed $num_passes out of $num_checks checks in $0"
test ${num_checks} = ${num_passes}
