#!/bin/sh
if ! which landslide
then
    set -x
    git clone https://github.com/adamzap/landslide.git
    cd landslide
    python setup.py develop
    set +x
    cd - >/dev/null
fi

if ! test -d avalanche
then
    set -x
    git clone https://github.com/akrabat/avalanche.git
    set +x
fi

landslide peyotl-slides.cfg
landslide phylesystem-slides.cfg