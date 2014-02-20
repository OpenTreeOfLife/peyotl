#!/bin/sh
dir=$(dirname "$0")
inpnexson="${1}"
converter="${2}"
if ! test -f "${inpnexson}"
then
    echo "The first arg should be a NeXSON instance doc. ${inpnexson} does not exist"
    exit 1
fi
if which validate-nexml >/dev/null
then
    do_schema_validation="1"
else
    do_schema_validation="0"
    echo '"validate-nexml" was not found on the path. Validation against schema will be skipped.'
fi
# 1. to NeXML
if ! python "$converter" "${inpnexson}" -o .1.xml
then
    echo "Conversion of \"${inpnexson}\" to JSON failed"
    exit 1
fi

# 2. validate NeXML
if test ${do_schema_validation} -eq "1"
then
    if ! validate-nexml .1.xml >/dev/null 2>&1
    then
        echo "XML written to .1.xml was not valid NeXML"
        exit 1
    fi
fi

# 3. Convert to back to JSON
if ! python "$converter" .1.xml -o .2.json
then
    echo "Conversion of .1.xml to JSON failed"
    exit 1
fi

python -c "import json, codecs, sys; o=codecs.open(sys.argv[2], 'w', encoding='utf-8'); json.dump(json.load(codecs.open(sys.argv[1], 'rU', encoding='utf-8')), o, indent=0, sort_keys=True); o.write('\n')" "${inpnexson}" .1.json
# 4. Verify that the input is valid NeXML
if ! diff .2.json .1.json
then
    echo "Did not roundtrip"
    exit 1
fi

if test "$3" = "-o"
then
    rm .1.json .1.xml .2.json 2>/dev/null
fi

