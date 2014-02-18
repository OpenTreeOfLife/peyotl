#!/bin/sh
dir="peyotl/test/data/nexson/${1}"
python scripts/nexson/nexson_nexml.py "${dir}/nexml" -e 1.2 > "${dir}/v1.2.json"
python scripts/nexson/nexson_nexml.py "${dir}/v1.2.json" -e 0.0 > "${dir}/v0.0.json"
python scripts/nexson/nexson_nexml.py "${dir}/v1.2.json" -e 1.0 > "${dir}/v1.0.json"
