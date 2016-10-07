#!/bin/bash
# Currently mis-named in that this script only tests nexson conversion. The intent was to add more small workflows
# here that utilize multiple tools (as opposed to just unit-tests).
#
source tests/bash-test-helpers.bash || exit
demand_at_top_level || exit

#set -x
top_dir="$(pwd)"
sn=$(basename "$0")
r=0 # the number of tests
p=0 # the number passed

# run shell scripts in the peyotl test dir
cd peyotl/test || exit

converter="${top_dir}/scripts/nexson/nexson_nexml.py"
if which xmllint 1>/dev/null 2>&1
then
    if which saxon-xslt 1>/dev/null 2>&1
    then
        r=$(expr 1 + ${r})
        if ./check_nexml_roundtrip.sh data/nexson/otu/nexml "${converter}" -o
        then
            p=$(expr 1 + ${p})
        else
            echo "${sn}: Failure of \" ${PWD}/check_nexml_roundtrip.sh ${PWD}/data/nexson/otu/nexml "${converter}" -o\""
        fi
    else
        echo "${sn}: nexml roundtrip test skipped due to lack of saxon-xslt"
    fi
else
    echo "${sn}: nexml roundtrip test skipped due to lack of xmllint"
fi

r=$(expr 1 + ${r})
if ./check_nexson_roundtrip.sh data/nexson/otu/v1.0.json "${converter}" -o 
then
    p=$(expr 1 + ${p})
else
    echo "${sn}: Failure of \"${PWD}/check_nexson_roundtrip.sh ${PWD}/data/nexson/otu/v1.0.json "${converter}" -o \""
fi


for d in otu 9
do
    r=$(expr 1 + ${r})
    if ./check_nexson_nexml_clique.sh data/nexson/${d}/v1.2.json "${converter}" 
    then
        p=$(expr 1 + ${p})
    else
        echo "${sn}: Failure of \"${PWD}/check_nexson_nexml_clique.sh ${PWD}/data/nexson/${d}/v1.0.json "${converter}"\""
    fi
done
cd -

cd "${cwd}"
if test ${r} -eq ${p}
then
    f=0
    echo "Passed all ($r) shell script tests."
else
    f=1
    echo "Passed only $p / $r shell script tests."
fi
exit ${f}
