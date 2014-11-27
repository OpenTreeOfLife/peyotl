#!/usr/bin/env python
from peyotl.ott import create_pruned_and_taxonomy_for_tip_ott_ids
from peyotl.utility import any_early_exit
def evaluate_tree_rooting(nexson, ott, tree_proxy):
    '''
    Returns None if the taxanomy contributes no information to the rooting decision
        (e.g. all of the tips are within one genus in the taxonomy)

    TODO: need to coordinate with Jim Allman and see if we can
    do this in a non- O(nm) manner (where n and m are the # of non-trivial edges in the phylo and taxo tree)
    putting barrier notes on the phylo tree would work...

    Adds the following properties to each edge in a the tree:
        UNROOTED_TAXO_STATUS_PROP -> facet of UnrootedConflictStatus
        CURRENT_ROOTING_COMPAT -> boolean relevant to EQUIVALENT and RESOLVES settings
        UNROOTED_CONFLICTS = list of IDs in the taxonomy tree that this edge will
            conflict with regardless of rooting.
        CURRENT_ROOTING_CONFLICTS = list of IDs in the taxonomy tree that this edge will
            conflicts in the current rooting.
   Adds the following properties to each non-tip-node and edge:
        ROOT_HERE_CONFLICTS = list of IDs in the taxonomy tree will be in conflict if we root the tree here.
        ROOT_HERE_AGREES = references to clades in the taxonomy tree that will be satisfied if we root the
            tree here.
    '''
    pruned_phylo, taxo_tree = create_pruned_and_taxonomy_for_tip_ott_ids(tree_proxy, ott)
    if taxo_tree is None: # this can happen if no otus are mapped
        return None
    has_taxo_groupings = any_early_exit(taxo_tree.root.child_iter(), lambda nd: not nd.is_leaf)
    if not has_taxo_groupings:
        return None
    has_phylo_groupings = any_early_exit(pruned_phylo.root.child_iter(), lambda nd: not nd.is_leaf)
    if not has_phylo_groupings:
        return None
    id2bit = pruned_phylo.add_bits4subtree_ids(None)
    taxo_tree.add_bits4subtree_ids(id2bit)
    for node in pruned_phylo:
        print node._id


