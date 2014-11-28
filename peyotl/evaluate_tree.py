#!/usr/bin/env python
from peyotl.ott import create_pruned_and_taxonomy_for_tip_ott_ids
from peyotl.phylo.compat import compare_bits_as_splits, SplitComparison
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
    taxo_nontriv_splits = taxo_tree.bits2internal_node
    taxon_mask = taxo_tree.root.bits4subtree_ids
    #_LOG.debug('taxo_nontriv_splits = {}'.format(taxo_nontriv_splits))
    # might want to copy this dict rather than modify in place..
    del taxo_nontriv_splits[taxon_mask] # root bitmask is trivial
    num_inf_taxo = len(taxo_nontriv_splits)
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
    _EMPTY_SET = frozenset([])
    non_root_pp_preorder = [nd for nd in pruned_phylo.preorder_node_iter()][1:]
    curr_root_incompat_set = set()
    any_root_incompat_set = set()
    _taxo_node_id_set_cache = {_EMPTY_SET: _EMPTY_SET}
    for node in non_root_pp_preorder:
        edge = node.edge
        if node.is_leaf:
            edge._displays = None
            edge._inverted_displays = None
            b = id2bit[node._id]
            if node._id in basal_taxo:
                edge._not_inverted_incompat = _EMPTY_SET
                edge._inverted_incompat = _EMPTY_SET
                inv_mask = taxon_mask - b
                idisp = taxo_nontriv_splits.get(inv_mask)
                if idisp is not None:
                    edge._inverted_displays = idisp
            else:
                edge._not_inverted_incompat = _EMPTY_SET
                #TODO would be more efficient to jump to tip and walk back...
                b = id2bit[node._id]
                ii = set()
                for tb, tid in taxo_nontriv_splits.items():
                    if tb & b:
                        ii.add(tid)
                edge._inverted_incompat = _get_cached_set(ii, _taxo_node_id_set_cache)
                disp = taxo_nontriv_splits.get(b)
                if disp is not None:
                    edge._displays = disp
        else:
            #TODO this could be more efficient...
            b = node.bits4subtree_ids
            nii = set()
            ii = set()
            e = set()
            ie = set()
            displays = None
            inv_displays = None
            #TODO: this loop does not take advantage of the fact that
            #   taxo_nontriv_splits are splits from a tree (hence compatible with each other)
            for tb, tid in taxo_nontriv_splits.items():
                sp_result = compare_bits_as_splits(b, tb, taxon_mask)
                if sp_result == SplitComparison.UNROOTED_INCOMPATIBLE:
                    any_root_incompat_set.add(tid)
                    nii.add(tid)
                    ii.add(tid)
                elif sp_result == SplitComparison.UNROOTED_COMPAT:
                    nii.add(tid)
                elif sp_result == SplitComparison.ROOTED_COMPAT:
                    ii.add(tid)
                elif sp_result == SplitComparison.UNROOTED_EQUIVALENT:
                    ie.add(tid)
                    inv_displays = tid
                elif sp_result == SplitComparison.ROOTED_EQUIVALENT:
                    e.add(tid)
                    displays = tid
            edge._not_inverted_incompat = _get_cached_set(nii, _taxo_node_id_set_cache)
            edge._inverted_incompat = _get_cached_set(ii, _taxo_node_id_set_cache)
            edge._equiv = _get_cached_set(e, _taxo_node_id_set_cache)
            edge._inverted_equiv = _get_cached_set(ie, _taxo_node_id_set_cache)
            edge._displays = displays
            edge._inverted_displays = inv_displays
            curr_root_incompat_set.update(nii)
            # create a set to be filled in in the loop below (for each internal node)
            node._inc_contrib_rootward = set()
            node._displays_contrib_rootward = set()
    pproot = pruned_phylo.root
    pproot._incompat_if_rooted_below = set()
    pproot._inc_contrib_rootward = set()
    pproot._displays_contrib_rootward = set()
    for node in reversed(non_root_pp_preorder):
        edge = node.edge
        if node.is_leaf:
            edge._inc_contrib_rootward = _EMPTY_SET
            node._displays_contrib_rootward = _EMPTY_SET
        else:
            par = node.parent
            iaobc = set(edge._not_inverted_incompat)
            iaobc.update(node._inc_contrib_rootward)
            edge._inc_contrib_rootward = _get_cached_set(iaobc, _taxo_node_id_set_cache)
            par._inc_contrib_rootward.update(edge._inc_contrib_rootward)
            par._displays_contrib_rootward.update(node._displays_contrib_rootward)
            if edge._displays is not None:
                par._displays_contrib_rootward.add(edge._displays)

    _LOG.debug('# root _inc_contrib_rootward = {}'.format(pruned_phylo.root._inc_contrib_rootward))
    _LOG.debug('# curr_root_incompat_set = {}'.format(curr_root_incompat_set))
    pproot.rooting_here_incompat = _get_cached_set(pproot._inc_contrib_rootward, _taxo_node_id_set_cache)
    pproot.rooting_here_conf_score = len(pproot.rooting_here_incompat)
    pproot.rooting_here_displays = _get_cached_set(pproot._displays_contrib_rootward, _taxo_node_id_set_cache)
    pproot.rooting_here_disp_score = len(pproot.rooting_here_displays)
    pproot.rooting_here_score = (pproot.rooting_here_disp_score, pproot.rooting_here_conf_score)
    pproot._inc_contrib_tipward = _EMPTY_SET
    pproot._disp_contrib_tipward = _EMPTY_SET
    best_score = pproot.rooting_here_score
    best_rootings = [pproot]
    # now sweep up
    for node in non_root_pp_preorder:
        edge = node.edge
        parent = node.parent
        sib_inc_union = set()
        sib_disp = set()
        for sib in node.sib_iter():
            sib_inc_union.update(sib.edge._inc_contrib_rootward)
            sib_disp.update(sib._displays_contrib_rootward)
            if sib.edge._displays is not None:
                sib_disp.add(sib.edge._displays)
        # if we are visiting an internal node, we have to figure out the cost of
        #  rooting at the node too...
        if not node.is_leaf:
            icu = set()
            icu.update(edge._inverted_incompat)
            icu.update(sib_inc_union)
            icu.update(parent._inc_contrib_tipward)
            node._inc_contrib_tipward = _get_cached_set(icu, _taxo_node_id_set_cache)
            dci = set(sib_disp)
            if edge._inverted_displays is not None:
                dci.add(edge._displays)
            dci.update(parent._disp_contrib_tipward)
            node._disp_contrib_tipward = _get_cached_set(dci, _taxo_node_id_set_cache)

            rhi = set()
            rhi.update(icu)
            rhi.update(node._inc_contrib_rootward)
            node.rooting_here_incompat = _get_cached_set(rhi, _taxo_node_id_set_cache)
            rhd = set(node._displays_contrib_rootward)
            rhd.update(node._disp_contrib_tipward)
            node.rooting_here_displays = _get_cached_set(rhd, _taxo_node_id_set_cache)
            best_score, best_rootings = _check_for_opt_score(node, best_score, best_rootings)
        # figure out the # of conflicts if rooting on this edge...
        rhi = set()
        rhi.update(edge._inverted_incompat)
        rhi.update(sib_inc_union)
        edge.rooting_here_incompat = _get_cached_set(rhi, _taxo_node_id_set_cache)
        rhd = set(parent._disp_contrib_tipward)
        rhd.update(parent.rooting_here_displays)
        if edge._inverted_displays is not None:
            rhd.add(edge._inverted_displays)
        edge.rooting_here_displays = _get_cached_set(rhd, _taxo_node_id_set_cache)
        best_score, best_rootings = _check_for_opt_score(edge, best_score, best_rootings)

    _LOG.debug('best_score = {}'.format(best_score))
    _LOG.debug('best_rootings = {}'.format(best_rootings))

def _check_for_opt_score(entity, best, best_list):
    conf = len(entity.rooting_here_incompat)
    ds = len(entity.rooting_here_displays)
    entity.rooting_here_conf_score = conf
    entity.rooting_here_disp_score = ds
    entity.rooting_here_score = (entity.rooting_here_disp_score, entity.rooting_here_conf_score)
    high_disp, low_conf = best
    if ds > high_disp:
        best = entity.rooting_here_score
        best_list = [entity]
    elif ds == high_disp:
        if conf < low_conf:
            best = entity.rooting_here_score
            best_list = [entity]
        elif conf == low_conf:
            best_list.append(entity)
    return best, best_list
def _get_cached_set(s, dict_frozensets):
    fs = frozenset(s)
    return dict_frozensets.setdefault(fs, fs)
