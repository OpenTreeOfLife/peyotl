#!/usr/bin/env bash

# This quick-and-dirty is for reconstructing a complete history for the
# collections-1 repo. It might never be used again as-is, but it might be
# helpful to someone else. This script assumes that:
#  - peyotl repo is available in the local filesystem
#  - user is in a venv or other python environment with required dependencies
#  - user has sudo privileges (required for peyotl log)

export TREE_RANKS_PATH=~/projects/nescent/opentree/synthesis_trees/Source_info/Tree_ranks

# v1 
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v1/fungi.py            > v1/fungi.json
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v1/metazoa.py          > v1/metazoa.json
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v1/microbes.py         > v1/microbes.json
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v1/plants.py           > v1/plants.json
echo "done with v1"

# v2 
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v2/fungi.py            > v2/fungi.json
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v2/metazoa.py          > v2/metazoa.json
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v2/safe_microbes.py    > v2/safe-microbes.json
# NOTE the use of a slug-friendly output filename (hyphens instead of underscores!)
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v2/plants.py           > v2/plants.json
# NOTE that we should use 'git mv' to track the renamed microbes file!
echo "done with v2"

# v3 
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v3/fungi.py            > v3/fungi.json
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v3/metazoa.py          > v3/metazoa.json
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v3/safe_microbes.py    > v3/safe-microbes.json
# NOTE the use of a slug-friendly output filename (hyphens instead of underscores!)
echo "."
sudo python tree-ranks-to-collection.py ${TREE_RANKS_PATH}/v3/plants.py           > v3/plants.json
echo "done with v3"

# Next we'd copy these .json files into the collections-1 repo, in 
#   /collections-by-owner/opentreeoflife/
# From each version folder in turn, copy the .json files in place, then commit.
# If a collection has been renamed, be sure to use 'git mv' to track this.
