#!/bin/sh
set -x
fn="$1"
converter="$2"
dir=$(dirname "$0")
if ! test -d scratch
then
    mkdir scratch || exit
fi
if ! test -e "${converter}"
then
    echo Expecting "${converter}" to be an executable.
    exit 1
fi

#all four edges from 1.2
for out in "1.2" "1.0" "0.0" "nexml"
do
    "${converter}" -e $out -s "$fn" -o scratch/.clique.v${out}from1.2.json || exit
done


for out in "nexml" "1.2" "1.0" "0.0"
do
    for inp in "nexml" "1.2" "1.0" "0.0"
    do
        inpf="scratch/.clique.v${inp}from1.2.json"
        outpf="scratch/.clique.v${out}from${inp}.json"
        if ! test $inpf = $outpf
        then
            "${converter}" -e $out -s  -o $outpf $inpf|| exit
        fi
    done
done

for out in "1.2" "1.0" "0.0"
do
    for inp in "1.2" "1.0" "0.0"
    do
        inpf="scratch/.clique.v${inp}from1.2.json"
        outpf="scratch/.clique.v${inp}from${out}.json"
        if ! test $inpf = $outpf
        then
            if ! diff $outpf $inpf
            then
                echo $outpf does not equal $inpf
                exit 1
            fi
        fi
    done
done
