#!/bin/sh
for i in $(ls *.output)
do
    e=$(echo $i | sed -E 's/.output/.expected/')
    if ! diff $e $i >/dev/null
    then
        kdiff3 $i $e
    fi
done