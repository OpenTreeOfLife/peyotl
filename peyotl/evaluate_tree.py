#!/usr/bin/env python
from peyotl.ott import create_pruned_and_taxonomy_for_tip_ott_ids
from peyotl.utility import any_early_exit, get_logger
from peyotl.utility.str_util import reverse_dict
_LOG = get_logger(__name__)
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
    bit2id = reverse_dict(id2bit)
    taxo_tree.add_bits4subtree_ids(id2bit)
    assert taxo_tree.root.bits4subtree_ids == pruned_phylo.root.bits4subtree_ids
    # might want to copy this dict rather than modify in place..
    taxo_nontriv_splits = taxo_tree.bits2internal_node
    taxon_mask = taxo_tree.root.bits4subtree_ids
    #_LOG.debug('taxo_nontriv_splits = {}'.format(taxo_nontriv_splits))
    del taxo_nontriv_splits[taxon_mask] # root bitmask is trivial
    _LOG.debug('taxon_mask = {} (which is {} bits)'.format(bin(taxon_mask)[2:], len(bin(taxon_mask)) - 2))
    num_ids = len(id2bit)
    _LOG.debug('id2bit has length = {}'.format(len(id2bit)))
    incompat_taxo_splits = {}
    #for checking tips of the phylogeny, it is nice to know which leaf OTUs attach 
    #   at the base of the taxonomy (no other grouping)
    basal_taxo = set()
    basal_bits = 0
    for c in taxo_tree.root.child_iter():
        if c.is_leaf:
            basal_taxo.add(c._id)
            basal_bits |= id2bit[c._id]
    _LOG.debug('basal_bits = {}'.format(bin(basal_bits)[2:].zfill(num_ids)))
    _LOG.debug('# nontrivial taxo splits = {}'.format(len(taxo_nontriv_splits)))
    for node in pruned_phylo:
        if node.is_leaf:
            pass # print node._id


