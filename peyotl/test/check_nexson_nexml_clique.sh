#!/bin/sh
fn="$1"
converter="$2"
dir=$(dirname "$0")
"${converter}" -m jj "$fn" -o .1.json || exit
diff "${fn}" .1.json || exit
"${converter}" -m jx "$fn" -o .1.xml || exit
"${converter}" -m xj .1.xml -o .3.json || exit
diff "${fn}" .3.json || exit
"${converter}" -m jb "$fn" -o .1.bf.json || exit
"${converter}" -m xx .1.xml -o .2.xml || exit
diff .1.xml .2.xml || exit
"${converter}" -m bb .1.bf.json -o .2.bf.json || exit
diff .1.bf.json .2.bf.json || exit
"${converter}" -m xb .1.xml -o .3.bf.json || exit
diff .2.bf.json .3.bf.json || exit
"${converter}" -m xj .1.xml -o .3.json || exit
diff "${fn}" .3.json || exit
"${converter}" -m bj .1.bf.json -o .4.json || exit
diff "${fn}" .4.json || exit
"${converter}" -m bx .1.bf.json -o .3.xml || exit
diff .1.xml .3.xml || exit
rm .1.bf.json .2.bf.json .3.bf.json .3.json .3.xml .4.json
#echo "${fn} passed clique test"