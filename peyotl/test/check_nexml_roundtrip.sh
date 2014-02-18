#!/bin/sh
dir=$(dirname "$0")
converter="${2}"
inpnexml="${1}"
if ! test -f "${inpnexml}"
then
    echo "The first arg should be a nexml instance doc. ${inpnexml} does not exist"
    exit 1
fi
if which validate-nexml >/dev/null
then
    do_schema_validation="1"
else
    do_schema_validation="0"
    echo '"validate-nexml" was not found on the path. Validation against schema will be skipped.'
fi

if ! test "$3" = "-o"
then
    if test -f .1.json -o -f .2.xml -o -f .pp2.xml -o -f .pp2.xml
    then
        echo "file .# or .pp# files in the way and the -o was not used as the 2nd arg"
        exit 1
    fi
fi

# 1. Verify that the input is valid NeXML

if test ${do_schema_validation} -eq "1"
then
    inpwasvalid=1
    if ! validate-nexml "${inpnexml}" >/dev/null 2>&1
    then
        echo "${inpnexml} is not a valid NeXML file"
        inpwasvalid=0
    fi
fi

# 2. Convert to JSON
if ! python "$converter" "${inpnexml}" -o .1.json
then
    echo "Conversion of \"${inpnexml}\" to JSON failed"
    exit 1
fi

# 3. Convert back to NeXML
if ! python "$converter" .1.json -o .2.xml
then
    echo "Conversion of .1.json to XML failed"
    exit 1
fi

# 4. validate NeXML
if test ${do_schema_validation} -eq "1"
then
    if ! validate-nexml .2.xml >/dev/null 2>&1
    then
        echo "XML written to .2.xml was not valid NeXML"
        if test $inpwasvalid -eq 1
        then
            exit 1
        fi
    fi
fi
# 5. verify that after pretty printing and culling of unstable aspects of the file
# the input and output are identical
# pretty print
xmllint --format "${inpnexml}" > .pp1.xml || exit
xmllint --format .2.xml > .pp2.xml || exit

# pretty print
saxon-xslt .pp1.xml "${dir}/sortattr.xslt" > .s1.xml || exit
saxon-xslt .pp2.xml "${dir}/sortattr.xslt" > .s2.xml || exit

# clean by getting rid of hard-to-standardize xml decl and generator field in top element
sed -e '/<\?xml version/d' .s1.xml | sed -e 's/<nex\(.*\)generator="[^"]*"/<nex\1/' > .cpp1.xml
sed -e '/<\?xml version/d' .s2.xml | sed -e 's/<nex\(.*\)generator="[^"]*"/<nex\1/' > .cpp2.xml

if ! diff .cpp1.xml .cpp2.xml
then
    echo "Did not roundtrip"
    exit 1
fi

if test "${3}" = "-o"
then
    rm -f .1.json .2.xml .cpp1.xml .cpp2.xml .pp1.xml .pp2.xml .s1.xml .s2.xml 2>/dev/null
fi
