# peyotl gcmdr
At this point, this is a proof of concept/test of peyotl. The goal is to have
wrappers around treemachine working well enough that it is easy to do what 
gcmdr (https://github.com/OpenTreeOfLife/gcmdr ) does.

peyotl/scripts/gcmdr.py is command line interface for some common actions, that uses
command line args and (primarily) INI-style config files. to control the synthesis steps.

## Example
If you a have a PEYOTL_CONFIG_FILE with the config settings (see below)

if you cd to a checked version of the gcmdr repo (so that you have the correct filepaths to 
the asterales inputs) then you should be able to:

    $ ${PEYOTL_ROOT}/extras/gcmdr/asterales/gcmdr-repo-run-asterales.sh

assuming that PEYOTL_ROOT points to the top of your clone of the peyotl repo. You can
check out that gcmdr-repo-run-asterales.sh to get a sense of how it works. Note that 
your peyotl-level config file can omit the variables that are specified in 
`${PEYOTL_ROOT}/extras/gcmdr/asterales/gcmdr-repo.config`

## currently used config vars

    [treemachine]
    nexson_cache = output path to a directory to store the nexsons
    synth_ott_id = ott ID of the root (I think)
    jar = input filepath to treemachine jar
    out_tree_file = output file of trees from each load and the last line will be the synthetic tree
    java = java -Xmx8g # or something similar. cmd line args to java
    log = output file path for treemachine log
    synthesis_db = output filepath that will be a dir with the neo-4j db with the synthetic tree
    load_db = output filepath that will be a dir with the neo-4j db with the loaded trees
    tax_db = output filepath that will be a dir with the neo-4j db with the taxonomy loaded
    loaded_trees_json = output filepath used to keep track of what trees have been loaded

    [phylesystem]
    parent = parent of the phylesystem repo checked out on your machine (but see bug below)

    [ott]
    parent = input dir that holds the OTT style taxonomy.tsv and synonyms.tsv and version.txt



#known bugs

1. It still pays attention to your peyotl-wide config file for the source of the phylesystem dir

2. does not clear the tree log when you refrest the tree db.

