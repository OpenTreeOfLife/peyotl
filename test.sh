#!/bin/sh
r=0 # the number of tests
p=0 # the number passed

cwd="$(pwd)"
top_dir="$(dirname $0)"
cd "$top_dir"
top_dir="$(pwd)"

# run shell scripts in the peyotl test dir
cd peyotl/test || exit

converter="${top_dir}/scripts/nexson/nexson_nexml.py"
if which xmllint 1>/dev/null 2>&1
then
    if which saxon-xslt 1>/dev/null 2>&1
    then
        r=$(expr 1 + $r)
        if ./check_nexml_roundtrip.sh data/nexson/otu.xml "${converter}" -o
        then
            p=$(expr 1 + $p)
        fi
    else
        echo "nexml roundtrip test skipped due to lack of saxon-xslt"
    fi
else
    echo "nexml roundtrip test skipped due to lack of xmllint"
fi

r=$(expr 1 + $r)
if ./check_nexson_roundtrip.sh data/nexson/otu-v1.0-nexson.json "${converter}" -o 
then
    p=$(expr 1 + $p)
fi

r=$(expr 1 + $r)
if ./check_nexson_nexml_clique.sh data/nexson/otu-v1.0-nexson.json "${converter}" 
then
    p=$(expr 1 + $p)
fi
cd -

if python setup.py test
then
    f=0
else
    f=1
fi

cd "${cwd}"
if test $r -eq $p
then
    echo "Passed all ($r) shell script tests."
else
    f=$(expr 1 + $f)
    echo "Passed only $p / $r shell script tests."
fi
exit $f