#!/usr/bin/env python
from peyotl.utility.str_util import is_str_type
from peyotl.phylo.tree import create_tree_from_id2par
from peyotl.manip import NexsonTreeProxy
from peyotl.ott import OTT
from copy import copy
from enum import Enum
class UnrootedConflictStatus(Enum):
    EQUIVALENT = 0
    INCOMPATIBLE = 1
    RESOLVES = 2 # compatible with "other" tree, and split is not in that tree
    TRIVIAL = 3 # will be compatible with any taxonomy
    NOT_COMPARABLE = 4 # e.g. lacking an OTT ID in a comparison to taxonomy
class CompatStatus(Enum):
    EQUIVALENT = 0
    CONFLICTS_WITH_ROOTED = 1
    CONFLICTS_WITH_UNROOTED = 2
    RESOLVES = 3
    RESOLVED_BY = 4
UNROOTED_TAXO_STATUS_PROP = '^ot:rootingInvariantTaxoContrastStatus'
CURRENT_ROOTING_COMPAT = '^ot:taxoCompatibleInCurrentRooting'
UNROOTED_CONFLICTS = '^ot:taxoEdgeConflictsAnyRooting'
CURRENT_ROOTING_CONFLICTS = '^ot:taxoEdgeConflictsCurrentRooting'
ROOT_HERE_CONFLICTS = '^ot:taxoEdgeConflictsIfRootedHere'
ROOT_HERE_AGREES = '^ot:taxoEdgeCompatibleIfRootedHere'
def evaluate_tree_rooting(nexson, ott, tree_proxy):
    ''' TODO: need to coordinate with Jim Allman and see if we can
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
    preorder_list = []
    ott_ids = []
    # create and id2par that has ott IDs only at the tips (we are
    #   ignoring mappings at internal nodes.
    # OTT IDs are integers, and the nodeIDs are strings - so we should not get clashes. #TODO consider prefix scheme
    ottId2OtuPar = {}
    # unwrapped proxy iteration
    for el in tree_proxy:
        preorder_list.append(el)
        node_id, node, edgeid, edge = el
        if tree_proxy.is_leaf(node_id):
            assert node_id == edge['@target']
            ott_id = tree_proxy.get_ott_id(node)
            if ott_id is not None:
                tree_proxy.annotate(edge, UNROOTED_TAXO_STATUS_PROP, UnrootedConflictStatus.NOT_COMPARABLE.name)
            else:
                tree_proxy.annotate(edge, UNROOTED_TAXO_STATUS_PROP, UnrootedConflictStatus.TRIVIAL.name)
                ott_ids.append(ott_id)
                assert isinstance(ott_id, int)
                parent_id = edge['@source']
                ottId2OtuPar[ott_id] = parent_id
        else:
            assert is_str_type(node_id)
            if edge is not None:
                parent_id = edge['@source']
                ottId2OtuPar[node_id] = parent_id
                assert node_id == edge['@target']
            else:
                ottId2OtuPar[node_id] = None
    pruned_phylo = create_tree_from_id2par(ottId2OtuPar, ott_ids)
    taxo_tree = ott.induced_tree(ott_ids)
    _markup_focal_tree_compat(ott_ids, pruned_phylo, preorder_list, taxo_tree)

class SplitComparison(Enum):
    INCOMPATIBLE = 0
    EQUIVALENT = 1
    COMPATIBLE_ANY_ROOTING_OF_FIRST = 2
    COMPATIBLE_SOME_ROOTING_OF_FIRST = 2
def are_rooted_compat(one_set, other):
    if one_set.issubset(other) or other.issubset(one_set):
        return True
    inter = one_set.intersection(other)
    return not bool(inter)

def unrooted_compatible(one_set, other, el_universe):
    if one_set.issubset(other) or other.issubset(one_set):
        if one_set == other:
            return SplitComparison.EQUIVALENT
        return SplitComparison.COMPATIBLE_ANY_ROOTING_OF_FIRST
    inter = one_set.intersection(other)
    if not bool(inter):
        if len(one_set) + len(other) == len(el_universe):
            return SplitComparison.EQUIVALENT
        return SplitComparison.COMPATIBLE_ANY_ROOTING_OF_FIRST
    if len(inter) + len(one_set) + len(other) == len(el_universe):
        return SplitComparison.COMPATIBLE_SOME_ROOTING_OF_FIRST
    return SplitComparison.INCOMPATIBLE

def _partition_by_compat(unrooted_d, rooted_d, id_universe):
    '''Partitions unrooted_d into 2 dicts:
        one with keys that are unrooted incompatible with the keys of rooted_id (value = list of values of rooted_d)
        the other with keys that are compatible (and the original value)
    '''
    incompat = {}
    compat_any_rooting = {}
    compat_some_rooting = {}
    edict = {}
    for tk, tv in unrooted_d.items():
        inc_list = []
        equiv = None
        any_rooting = True
        for rk, rv in rooted_d.items():
            comp = unrooted_compatible(tk, rk, id_universe)
            if comp == SplitComparison.INCOMPATIBLE:
                inc_list.append(rv)
            elif comp == SplitComparison.EQUIVALENT:
                equiv = rv
                break # we assume that rooted_d is from a tree
            elif comp == SplitComparison.COMPATIBLE_SOME_ROOTING_OF_FIRST:
                any_rooting = False
        if inc_list:
            incompat[tv] = inc_list
        elif equiv is None:
            if any_rooting:
                compat_any_rooting[tk] = tv
            else:
                compat_some_rooting[tk] = tv
        else:
            edict[tk] = (tv, equiv)

    return incompat, compat_any_rooting, compat_some_rooting, edict
def compatible_with_rooting(phylo_mrca, rooting_mrca, taxo_mrca, id_set):
    if rooting_mrca.issubset(phylo_mrca) and rooting_mrca != phylo_mrca:
        # considering reversing order of this split
        phylo_mrca = id_set - phylo_mrca
    else:
        assert phylo_mrca.issubset(rooting_mrca) or len(phylo_mrca.intersection(rooting_mrca)) == 0
    return are_rooted_compat(phylo_mrca, taxo_mrca)
def _eval_root_here(phylo_mrca, node_id, rooting_mrca, ctd, id_set, root_here_agrees, root_here_conflicts):
    for taxo_mrca, taxo_id in ctd.items():
        if compatible_with_rooting(phylo_mrca, rooting_mrca, taxo_mrca, id_set):
            root_here_agrees.add(taxo_id)
        else:
            root_here_conflicts.setdefault(taxo_id, set()).add(node_id)
def _do_eval_root_here(phylo_mrca, node_id, rooting_mrca, ctd, id_set): #TODO ridiculously slow way to do this...
    a, c = set(), {}
    _eval_root_here(phylo_mrca, node_id, rooting_mrca, ctd, id_set, a, c)
    return len(c) == 0

def _markup_focal_tree_compat(id_list, focal_tree, preorder_list, comp_tree):
    ''' `focal_tree` is the one to be marked-up. We are considering rerooting it.
    `comp_tree's rooting is not questioned.

    sweeps over the internal nodes of focal tree. Marks each edge as:
        EQUIVALENT + ref to corresponding node in comp_tree
        CONFLICTS_WITH_ROOTED + ref to one of the nodes in comp_tree that it conflicts with
        CONFLICTS_WITH_UNROOTED + ref to one of the edges in comp_tree that it conflicts with
        RESOLVES + ref to node that is the most recent node in comp_tree with a superset of the ingroup
    '''
    id_set = frozenset(id_list)
    focal_tree.add_mrca_id_sets(id_set) #TODO could reduce memory by creating mrca sets during traversal
    comp_tree.add_mrca_id_sets(id_set)

    focal_tree.write_newick(sys.stdout)
    comp_tree.write_newick(sys.stdout)
    #_LOG.debug('focal_tree mrca set = {}'.format(focal_tree._root.mrca_of_leaf_ids))
    #_LOG.debug('comp_tree mrca set = {}'.format(comp_tree._root.mrca_of_leaf_ids))
    it = iter(comp_tree.preorder_node_iter())
    ct_root = next(it)
    assert ct_root._parent is None
    ctd = {}
    for cn in it:
        if not cn.is_leaf:
            _LOG.debug('internal: {}'.format(cn._id))
            cn.mrca_of_leaf_ids = frozenset(cn.mrca_of_leaf_ids)
            ctd[cn.mrca_of_leaf_ids] = cn
    ftd = {}
    fnid2mrca = {}
    # unwrapped proxy iteration
    for el in reversed(preorder_list):
        node_id, node, edgeid, edge = el
        if tree_proxy.is_leaf(node_id):
            ott_id = tree_proxy.get_ott_id(node)
            mrca = frozenset([ott_id])
        else:
            mrca = set()
            for cel in tree_proxy.child_iter(node_id):
                cnode_id, cnode, cedgeid, cedge = cel
                cmrca = fnid2mrca[cnode_id]
                mrca.update(cmrca)
            mrca = frozenset(mrca)
            if edge is not None:
                ftd[mrca] = (node, edge)
        fnid2mrca[node_id] = mrca
    # ftd now holds the non-trivial splits. First we'll partition them into
    # those that are incompatible with the comp_tree in an unrooted sense...
    part_result = _partition_by_compat(fnid2mrca, ctd, id_set)
    incompat, compatAnyFnid2mrca, compatSomeFnid2mrca, equiv = part_result

    # TODO this could be a lot more efficient worst case here is O(n^2 m) where n is the # of non-trivial splits in tree_proxy
    # unwrapped proxy iteration
    root_here_agrees_base = set([i for i in compatAnyFnid2mrca.values()]) # shouldn't include this everywhere unless Jim needs it...
    for el in tree_proxy:
        preorder_list.append(el)
        node_id, node, edgeid, edge = el
        if tree_proxy.is_leaf(node_id):
            assert node_id == edge['@target']
            rooting_mrca = fnid2mrca[node_id]
            tree_proxy.annotate(edge, CURRENT_ROOTING_COMPAT, True)
            tree_proxy.annotate(edge, UNROOTED_CONFLICTS, [])
            tree_proxy.annotate(edge, CURRENT_ROOTING_CONFLICTS, [])
        else:
            assert node_id == edge['@target']
            rooting_mrca = fnid2mrca[node_id]
            if node_id in incompat:
                tree_proxy.annotate(edge, CURRENT_ROOTING_COMPAT, False)
            else:
                r = _do_eval_root_here(rooting_mrca, node_id, id_set, ctd, id_set)
                tree_proxy.annotate(edge, CURRENT_ROOTING_COMPAT, r)
            tree_proxy.annotate(edge, UNROOTED_CONFLICTS, [])
            tree_proxy.annotate(edge, CURRENT_ROOTING_CONFLICTS, [])
        root_here_agrees = copy(root_here_agrees_base)
        root_here_conflicts = {}
        for phylo_mrca, node_id in compatSomeFnid2mrca.items():
            _eval_root_here(phylo_mrca, node_id, rooting_mrca, ctd, id_set, root_here_agrees, root_here_conflicts)
        for phylo_mrca, pairing in compatSomeFnid2mrca.items():
            node_id = pairing[0] #TODO should special case this one..
            _eval_root_here(phylo_mrca, node_id, rooting_mrca, ctd, id_set, root_here_agrees, root_here_conflicts)
        tree_proxy.annotate(edge, ROOT_HERE_AGREES, root_here_agrees)
        tree_proxy.annotate(edge, ROOT_HERE_CONFLICTS, root_here_conflicts)
        if tree_proxy.is_leaf(node_id):
            taxo_id = ctd.get(rooting_mrca)
            if taxo_id is not None:
                rha = copy(root_here_agrees)
                rhc = copy(root_here_conflicts)
                rha.remove(taxo_id)
                rhc.setdefault(taxo_id, set()).add(node_id)
                add
                  to 
                    node
        
    '''assert focal_tree._root.mrca_of_leaf_ids == id_set
    assert comp_tree._root.mrca_of_leaf_ids == id_set
    for fnode in focal_tree.postorder_node_iterd:
        if fnode.is_leaf:
            fnode._corresponding_node = comp_tree.find_node(fnode._id)
            fnode._status = ConflictStatus.TRIVIAL
        else:
            status, corr_node = _check_for_split_status(fnode.mrca_of_leaf_ids,
                                                        fnode._children[0]._corresponding_node,
                                                        comp_tree,
                                                        id_set)
def _assess_compat(clade, other, id_set, num_ids):
    d = clade - other
    if d:
        e = other - clade
        if e:
            ld = len(d)
            if ld + len(other) == num_ids:
                le = len(e)
                return CompatStatus.CONFLICTS_WITH_ROOTED, min(ld, le, num_ids - ld - le)
            return CompatStatus.CONFLICTS_WITH_UNROOTED, 0
        return CompatStatus.RESOLVED_BY, len(d)
    e = other - clade
    if e:
        return CompatStatus.RESOLVES, len(e)
    return CompatStatus.EQUIVALENT, 0

def _check_for_split_status(ingroup_ids, start_node, comp_tree, id_set):
    candidates = {}
    tried = set()
    num_ids = len(id_set)
    if start_node.is_leaf:
        start_node = start_node._parent
        assert start_node is not None
    p = start_node._parent
    if p is not None:
        candidates[p._id] = p
    tried = start_node._id
    compat, size_diff = _assess_compat(ingroup_ids, start_node.mrca_of_leaf_ids, id_set, num_ids)
    if compat == CompatStatus.EQUIVALENT or compat == CompatStatus.CONFLICTS_WITH_UNROOTED:
        return compat, start_node
    if compat == 
'''
if __name__ == '__main__':
    from peyotl.utility.input_output import read_as_json
    from peyotl.nexson_syntax import convert_nexson_format, BY_ID_HONEY_BADGERFISH, extract_tree_nexson
    from peyotl import get_logger
    import argparse
    import codecs
    import json
    import sys
    import os
    SCRIPT_NAME = os.path.split(os.path.abspath(sys.argv[0]))[-1]
    _LOG = get_logger(SCRIPT_NAME)
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

    parser = argparse.ArgumentParser(description='Suggest rootings based on OTT for a tree')
    parser.add_argument('--verbose',
                        dest='verbose',
                        action='store_true',
                        default=False,
                        help='verbose output')
    parser.add_argument("-t", "--tree-id", 
                        metavar="TREEID",
                        required=False,
                        default=None,
                        help="The ID of the tree to be analyzed (if omitted, all trees will be used).")
    parser.add_argument("-o", "--output", 
                        metavar="FILE",
                        required=False,
                        help="output filepath. Standard output is used if omitted.")
    parser.add_argument('input',
                        metavar='filepath',
                        type=unicode,
                        nargs=1,
                        help='filename')
    err_stream = sys.stderr
    args = parser.parse_args()
    try:
        inp_filepath = args.input[0]
    except:
        sys.exit('Expecting a filepath to a NexSON file as the only argument.\n')
    outfn = args.output
    if outfn is not None:
        try:
            out = codecs.open(outfn, mode='w', encoding='utf-8')
        except:
            sys.exit('validate_ot_nexson: Could not open output filepath "{fn}"\n'.format(fn=outfn))
    else:
        out = codecs.getwriter('utf-8')(sys.stdout)
    try:
        nexson = read_as_json(inp_filepath)
    except ValueError as vx:
        _LOG.error('Not valid JSON.')
        if args.verbose:
            raise vx
        else:
            sys.exit(1)
    except Exception as nx:
        _LOG.error(nx.value)
        sys.exit(1)
    convert_nexson_format(nexson, BY_ID_HONEY_BADGERFISH)
    trees = extract_tree_nexson(nexson, tree_id=args.tree_id)
    if len(trees) == 0:
        trees = extract_tree_nexson(nexson, tree_id=None)
        if trees:
            v = '", "'.join([i[0] for i in trees])
            sys.exit('Tree ID {i} not found. Valid IDs for this file are "{l}"\n'.format(i=args.tree_id, l=v))
        else:
            sys.exit('This NexSON has not trees.\n')
    ott = OTT()
    for tree_id, tree, otus in trees:
        tree_proxy = NexsonTreeProxy(tree=tree, tree_id=tree_id, otus=otus)
        evaluate_tree_rooting(nexson, ott, tree_proxy)

