#!/bin/bash
function demand_at_top_level {
    for d in peyotl extras scripts tutorials tests
    do
        if ! test -d "$d"
        then
            echo "$0 must be run from the PEYOTL_ROOT dir (the parent of the tests dir)."
            exit 1
        fi
    done
}

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
        if ! python tests/match_logger_output.py ${f} ${s}
        then
            echo "Format of messages in \"${s}\" was wrong"
            num_fails=$(expr 1 + ${num_fails})
        fi
    done
}

function demand_equal {
    num_checks=$(expr 1 + ${num_checks})
    if ! test "$1" = "$2"
    then
        echo "strings \"$1\" and \"$2\" differed."
        num_fails=$(expr 1 + ${num_fails})
    fi
}

function demand_empty_str {
    num_checks=$(expr 1 + ${num_checks})
    if ! test -z "$1"
    then
        echo "strings \"$1\" was not empty."
        num_fails=$(expr 1 + ${num_fails})
    fi
}

function refresh_and_test_local_git {
    if ! bash dev/refresh_for_git_tests.sh
    then
        echo "Could not run dev/refresh_for_git_tests.sh script!"
        num_fails=$(expr ${num_fails} + 1)
        exit 1
    fi
    num_checks=$(expr 1 + ${num_checks})
    if ! python $@
    then
        num_fails=$(expr ${num_fails} + 1)
    fi
}

function echo_and_demand_succeeds {
    echo $@
    num_checks=$(expr 1 + ${num_checks})
    if ! $@
    then
        num_fails=$(expr 1 + ${num_fails})
    fi
}
