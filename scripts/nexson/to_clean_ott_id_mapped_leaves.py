#!/usr/bin/env python
from peyotl.nexson_syntax import extract_tree_nexson, get_nexml_el
from peyotl import OTULabelStyleEnum
from peyotl import write_as_json, read_as_json
from peyotl.ott import OTT
from peyotl import get_logger
_LOG = get_logger(__name__)

from collections import defaultdict
_VERBOSE = True
def debug(msg):
    if _VERBOSE:
        sys.stderr.write(msg)
        sys.stderr.write('\n')

def to_edge_by_target_id(tree):
    '''creates a edge_by_target dict with the same edge objects as the edge_by_source'''
    ebt = {}
    ebs = tree['edgeBySourceId']
    for edge_dict in ebs.values():
        for edge_id, edge in edge_dict.items():
            target_id = edge['@target']
            edge['@id'] = edge_id
            assert target_id not in ebt
            ebt[target_id] = edge
    #check_rev_dict(tree, ebt)
    return ebt

def check_rev_dict(tree, ebt):
    '''Verifyies that `ebt` is the inverse of the `edgeBySourceId` data member of `tree`'''
    ebs = defaultdict(dict)
    for edge in ebt.values():
        source_id = edge['@source']
        edge_id = edge['@id']
        ebs[source_id][edge_id] = edge
    assert ebs == tree['edgeBySourceId']

def find_tree_and_otus_in_nexson(nexson, tree_id):
    tl = extract_tree_nexson(nexson, tree_id)
    assert len(tl) == 1
    tree_id, tree, otus = tl[0]
    return tree, otus

def prune_clade(edge_by_target, edge_by_source, node_id, nodes_deleted, edges_deleted):
    '''Prune `node_id` and the edges and nodes that are tipward of it.
    Caller must delete the edge to node_id.

    nodes_deleted, edges_deleted are lists of ids that will be appended to.
    '''
    to_del_nodes = [node_id]
    while bool(to_del_nodes):
        node_id = to_del_nodes.pop(0)
        nodes_deleted.append(node_id)
        del edge_by_target[node_id] # delete reference to parent edge
        ebsd = edge_by_source.get(node_id)
        if ebsd is not None:
            new_nodes = []
            for edge_id, edge in ebsd.items():
                edges_deleted.append(edge_id)
                new_nodes.append(edge['@target'])
            del edge_by_source[node_id] # deletes all of the edges out of this node (still held in edge_by_target til children are encountered)
            to_del_nodes.extend(new_nodes)

def prune_edge_and_below(edge_by_target, edge_by_source, edge_to_del, nodes_deleted, edges_deleted):
    while edge_to_del is not None:
        edge_id = edge_to_del['@id']
        t = edge_to_del['@target']
        del edge_by_target[t]
        source_id = edge_to_del['@source']
        ebsd = edge_by_source[source_id]
        del ebsd[edge_id]
        nodes_deleted.append(source_id)
        edges_deleted.append(edge_to_del)
        while True:
            for edge_id, edge in ebsd.items():
                edges_deleted.append(edge_id)
                node_id = edge['@target']
                prune_clade(edge_by_target, edge_by_source, node_id, nodes_deleted, edges_deleted)
            del edge_by_source[source_id]
        edge_to_del = edge_by_target.get(source_id)

def _prune_to_ingroup(edge_by_target, edge_by_source, ingroup_node, log_obj):
    '''Performs the actions of `prune_ingroup` when the ingroup is not the root'''
    edge_to_del = edge_by_target.get(ingroup_node)
    if edge_to_del is None:
        return
    nodes_deleted = []
    edges_deleted = []
    prune_edge_and_below(edge_by_target, edge_by_source, edge_to_del, nodes_deleted, edges_deleted)
    if log_obj is not None:
        log_obj['outgroup'] = {'nodes': nodes_deleted, 'edges': edges_deleted}

def prune_ingroup(tree, edge_by_target, edge_by_source, log_obj=None):
    '''Remove nodes and edges from `tree` if they are not the ingroup or a descendant of it.

    `tree` must be a HBF Nexson tree with each of its edge objects indexed in both
        `edge_by_target` and `edge_by_source`
    Returns the root of the pruned tree.
    If log_obj is not None, actions are stored in log_obj by overwriting the 'outgroup' key
        of that dict with {'nodes': nodes_deleted, 'edges': edges_deleted}
    '''
    # Prune to just the ingroup
    ingroup_node_id = tree.get('^ot:rootNodeId')
    root_node_id = tree['^ot:rootNodeId']
    if ingroup_node_id is None:
        _LOG.debug('No ingroup node specified.')
    elif ingroup_node_id != root_node_id:
        _prune_to_ingroup(edge_by_target, edge_by_source, ingroup_node_id, log_obj=log_obj)
        return ingroup_node_id
    else:
        _LOG.debug('Ingroup node is root.')
    return root_node_id

def group_and_sort_leaves_by_ott_id(tree, edge_by_target, edge_by_source, otus):
    '''returns a dict mapping ott_id to list of elements referring to leafs mapped
    to that ott_id. They keys will be ott_ids and None (for unmapped tips). The values
    are lists of tuples. Each tuple represents a different leaf and contains:
        (integer_for_of_is_examplar: -1 if the node is flagged by ^ot:isTaxonExemplar. 0 otherwise
        the leaf's node_id,
        the node object
        the otu object for the node
        )
    Side effects:
      - adds an @id element to each leaf node object in tree['nodeById']
    '''
    leaves = [i for i in edge_by_target.keys() if i not in edge_by_source]
    node_by_id = tree['nodeById']
    ott_id_to_sortable_list = defaultdict(list)
    leaf_ott_ids = set()
    has_an_exemplar_spec = set()
    for leaf_id in leaves:
        node_obj = node_by_id[leaf_id]
        node_obj['@id'] = leaf_id
        otu_id = node_obj['@otu']
        otu_obj = otus[otu_id]
        ott_id = otu_obj.get('^ot:ottId')
        is_exemplar = node_obj.get('^ot:isTaxonExemplar', False)
        int_is_exemplar = 0
        if is_exemplar:
            has_an_exemplar_spec.add(leaf_id)
            int_is_exemplar = -1 # to sort to the front of the list
        sortable_el = (int_is_exemplar, leaf_id, node_obj, otu_obj)
        ott_id_to_sortable_list[ott_id].append(sortable_el)
        if ott_id is not None:
            leaf_ott_ids.add(ott_id)
    for v in ott_id_to_sortable_list.values():
        v.sort()
    return ott_id_to_sortable_list


def suppress_deg_one_node(tree, edge_by_target, edge_by_source, to_par_edge, nd_id, to_child_edge, nodes_deleted, edges_deleted):
    '''Deletes to_par_edge and nd_id. To be used when nd_id is an out-degree= 1 node'''
    nodes_deleted.append(nd_id)
    to_par_edge_id = to_par_edge['@id']
    par = to_par_edge['@source']
    edges_deleted.append(to_par_edge_id)
    to_child_edge_id = to_child_edge['@id']
    del edge_by_source[par][to_par_edge_id]
    del edge_by_target[nd_id]
    del edge_by_source[nd_id]
    edge_by_source[par][to_child_edge_id] = to_child_edge
    to_child_edge['@source'] = par

def prune_deg_one_root(tree, edge_by_target, edge_by_source, orphaned_root, nodes_deleted, edges_deleted):
    new_root = orphaned_root
    ebs_el = edge_by_source[new_root]
    while len(ebs_el) == 1:
        edge = ebs_el.values()[0]
        del edge_by_source[new_root]
        nodes_deleted.append(new_root)
        new_root = edge['@target']
        del edge_by_target[new_root]
        edges_deleted.append(edge['@id'])
        ebs_el = edge_by_source.get(new_root)
        if ebs_el == None:
            return None
    return new_root

def prune_if_deg_too_low(tree, edge_by_target, edge_by_source, ind_nd_id_list, log_obj):
    nodes_deleted = []
    edges_deleted = []
    orphaned_root = None
    while bool(ind_nd_id_list):
        next_ind_nd_id_list = set()
        for nd_id in ind_nd_id_list:
            out_edges = edge_by_source.get(nd_id)
            if out_edges is None:
                out_degree == 0
            else:
                out_degree = len(out_edges)
            if out_degree < 2:
                to_par = edge_by_target.get(nd_id)
                if to_par:
                    par = to_par['@source']
                    next_ind_nd_id_list.add(par)
                    if out_degree == 1:
                        out_edge = out_edges.values()[0]
                        suppress_deg_one_node(tree,
                                              edge_by_target,
                                              edge_by_source,
                                              to_par, 
                                              nd_id,
                                              out_edge,
                                              nodes_deleted,
                                              edges_deleted)
                    else:
                        nodes_deleted.append(nd_id)
                        del edge_by_target[nd_id]
                        to_par_edge_id = to_par['@id']
                        edges_deleted.append(to_par_edge_id)
                        del edge_by_source[par][to_par_edge_id]
                    if nd_id in next_ind_nd_id_list:
                            next_ind_nd_id_list.remove(nd_id)
                else:
                    assert (orphaned_root is None) or (orphaned_root == nd_id)
                    orphaned_root = nd_id
        ind_nd_id_list = next_ind_nd_id_list
    if orphaned_root is not None:
        new_root = prune_deg_one_root(tree, edge_by_target, edge_by_source, orphaned_root, nodes_deleted, edges_deleted)
    else:
        new_root = None
    reason = 'became_trivial'
    l = log_obj.setdefault(reason, {'nodes':[], 'edges':[]})
    l['nodes'].extend(nodes_deleted)
    l['edges'].extend(edges_deleted)
    return new_root

def prune_tips(tree, edge_by_target, edge_by_source, leaf_el_list, reason, log_obj):
    par_to_check = set()
    nodes_deleted = []
    edges_deleted = []
    for leaf_el in leaf_el_list:
        int_is_exemplar, leaf_id, node, otu = leaf_el
        edge = edge_by_target[leaf_id]
        del edge_by_target[leaf_id]
        edge_id = edge['@id']
        edges_deleted.append(edge_id)
        source_id = edge['@source']
        del edge_by_source[source_id][edge_id]
        par_to_check.add(source_id)
        nodes_deleted.append(leaf_id)
    l = log_obj.setdefault(reason, {'nodes':[], 'edges':[]})
    l['nodes'].extend(nodes_deleted)
    l['edges'].extend(edges_deleted)
    return prune_if_deg_too_low(tree, edge_by_target, edge_by_source, par_to_check, log_obj)

def prune_tree_for_supertree(nexson,
                             tree_id,
                             ott,
                             log_obj):
    '''
    '''
    tree, otus = find_tree_and_otus_in_nexson(nexson, tree_id)
    if tree is None:
        raise KeyError('Tree "{}" was not found.'.format(tree_id))
    edge_by_target = to_edge_by_target_id(tree)
    edge_by_source = tree['edgeBySourceId']
    ingroup_node = prune_ingroup(tree, edge_by_target, edge_by_source, log_obj)
    by_ott_id = group_and_sort_leaves_by_ott_id(tree, edge_by_target, edge_by_source, otus)
    revised_ingroup_node = ingroup_node
    # Leaf nodes with no OTT ID at all...
    if None in by_ott_id:
        nr = prune_tips(tree, edge_by_target, edge_by_source, by_ott_id[None], 'unmapped_otu', log_obj)
        del by_ott_id[None]
        if nr is not None:
            revised_ingroup_node = nr
    # Check the stored OTT Ids against the current version of OTT
    mapped, unrecog, forward2unrecog, old2new = ott.map_ott_ids(by_ott_id.keys())
    for ott_id in unrecog:
        nr = prune_tips(tree, edge_by_target, edge_by_source, by_ott_id[ott_id], 'unrecognized_ott_id', log_obj)
        del by_ott_id[ott_id]
        if nr is not None:
            revised_ingroup_node = nr
    for ott_id in forward2unrecog:
        nr = prune_tips(tree, edge_by_target, edge_by_source, by_ott_id[ott_id], 'forwarded_to_unrecognized_ott_id', log_obj)
        del by_ott_id[ott_id]
        if nr is not None:
            revised_ingroup_node = nr
    for old_id, new_id in old2new.items():
        old_node_list = by_ott_id[old_id]
        del by_ott_id[ott_id]
        if new_id in by_ott_id:
            v = by_ott_id[new_id]
            v.extend(old_node_list)
            v.sort()
        else:
            by_ott_id = old_node_list
    lost_tips = set(unrecog)
    lost_tips.update(set(forward2unrecog))

    # Get the induced tree to look for leaves mapped to ancestors of other leaves
    ott_tree = ott.induced_tree(mapped)
    taxon_contains_other_ott_ids = []
    for ott_id in by_ott_id:
        if ott_id in lost_tips:
            continue
        ott_id = old2new.get(ott_id, ott_id)
        nd = ott_tree.find_node(ott_id)
        assert nd is not None
        print nd.children, dir(nd)
    sys.exit()
    common_anc_id_set = set()
    ca_rev_order = None
    anc_leaf_ott_ids = set()
    traversed_ott_ids = set()
    suppressed_by_anc_exemplar = defaultdict(list)
    for ott_id in leaf_ott_ids:
        ancs = ott.get_anc_lineage(ott_id)
        assert ancs.pop(0) == ott_id
        if not bool(ancs):
            continue
        if ca_rev_order is None:
            ca_rev_order = list(ancs)
            ca_rev_order.reverse()
            common_anc_id_set.update(set(ca_order))
        for anc in ancs:
            if anc in traversed_ott_ids:
                if anc in common_anc_id_set:
                    while ca_rev_order[-1] != anc:
                        x = ca_rev_order.pop()
                        common_anc_id_set.remove(x)
                break
            traversed_ott_ids.add(anc)
            if anc in leaf_ott_ids:
                if anc in has_an_exemplar_spec(anc):
                    if ott_id in has_an_exemplar_spec:
                        anc_leaf_ott_ids.add(anc)
                        has_an_exemplar_spec.remove(anc)
                        if anc in suppressed_by_anc_exemplar:
                            del suppressed_by_anc_exemplar[anc]
                    else:
                        suppressed_by_anc_exemplar[anc].append(ott_id)
                else:
                    anc_leaf_ott_ids.add(anc)
    all_suppressed_by_anc = set()
    for anc, des_list in suppressed_by_anc_exemplar.items():
        all_suppressed_by_anc.update(set(des_list))

    print leaf_ott_ids

if __name__ == '__main__':
    import argparse
    import codecs
    import sys
    import os
    description = ''
    parser = argparse.ArgumentParser(prog='to_clean_ott_id_mapped_leaves.py', description=description)
    parser.add_argument('nexson',
                        nargs="+",
                        type=str,
                        help='nexson files with the name pattern studyID_treeID.json')
    parser.add_argument('--ott-dir',
                        default=None,
                        type=str,
                        required=True,
                        help='directory containing ott files (e.g "taxonomy.tsv")')
    parser.add_argument('--out-dir',
                        default=None,
                        type=str,
                        required=True,
                        help='Output directory for the newick files.')
    parser.add_argument('--flags',
                        default=None,
                        type=str,
                        required=False,
                        help='Optional comma-separated list of flags to prune. If omitted, the treemachine flags are used.')
    args = parser.parse_args(sys.argv[1:])
    ott_dir, out_dir = args.ott_dir, args.out_dir
    flags_str = args.flags
    try:
        assert os.path.isdir(args.ott_dir)
    except:
        sys.exit('Expecting ott-dir argument to be a directory. Got "{}"'.format(args.ott_dir))
    ott = OTT(ott_dir=args.ott_dir)
    for inp in args.nexson:
        log_obj = {}
        study_tree = '.'.join(inp.split('.')[:-1]) # strip extension
        x = study_tree.split('_')
        if len(x) != 3:
            sys.exit('Currently using the NexSON file name to indicate the tree via: studyID_treeID.json. Expected exactly 2 _ in the filename.\n')
        tree_id = study_tree.split('_')[-1]
        nexson_blob = read_as_json(inp)
        prune_tree_for_supertree(nexson=nexson_blob,
                                 tree_id=tree_id,
                                 ott=ott,
                                 log_obj=log_obj)
        
    
    
    sys.exit(0)
    if flags_str is None:
        flags = ott.TREEMACHINE_SUPPRESS_FLAGS
    else:
        flags = flags_str.split(',')
    create_log = log_filename is not None
    with codecs.open(args.output, 'w', encoding='utf-8') as outp:
        log = ott.write_newick(outp,
                               label_style=OTULabelStyleEnum.CURRENT_LABEL_OTT_ID,
                               prune_flags=flags,
                               create_log_dict=create_log)
        outp.write('\n')
    if create_log:
        write_as_json(log, log_filename)
