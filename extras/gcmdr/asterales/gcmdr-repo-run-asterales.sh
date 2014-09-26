#!/bin/bash
if ! test -d example/aster
then
    echo 'expecting this to be executed from the gcmdr repo!. example/aster not found!'
    exit 1
fi
script_dir=$(dirname $0)
config="${script_dir}/gcmdr-repo.config"
if ! test -f "$config"
then
    echo Expecting the script to be the peyotl/extras/gcmdr/asterales dir. "${config}" not found!
    exit 1
fi
gcmdr_ex_dir=$(dirname "${script_dir}")
extras_dir=$(dirname "${gcmdr_ex_dir}")
peyotl_dir=$(dirname "${extras_dir}")
gcmdr_script="${peyotl_dir}/scripts/gcmdr.py"

#"$gcmdr_script" -c "${config}" taxonomy
#"$gcmdr_script" -c "${config}" --studies="${script_dir}/studies.txt" fetchNexsons --download
#"$gcmdr_script" -c "${config}" --studies="${script_dir}/studies.txt" loadGraph --reinitialize
"$gcmdr_script" -c "${config}" synthesize

