#!/usr/bin/env
from peyotl.api import APIWrapper
tm = APIWrapper().treemachine
tax = APIWrapper().taxomachine

# Get info about synthesis
info = tm.get_synthetic_tree_info()

# Get tree ID
tid = info['tree_id']

# Get the OTT IDs from taxomachine
human, gorilla = tax.names_to_ott_ids_perfect(['homo sapiens', 'Gorilla gorilla'])

mrca_info = tm.mrca(ott_ids=[human, gorilla])
mrca_node_id = mrca_info['mrca_node_id']

# fetch a few levels of the tree:
newick = tm.get_synthetic_tree(tid, format="newick", node_id=mrca_node_id)['newick']

# pruned is silly for just 2 leaves, but...
newick = tm.get_synth_tree_pruned(ott_ids=[human, gorilla])['subtree']

# Get list of dicts describing the version of each input tree
inputs = tm.get_synthetic_tree_id_list()
