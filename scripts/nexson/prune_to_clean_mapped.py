#!/usr/bin/env python
from peyotl.nexson_syntax import extract_tree_nexson, \
                                 get_nexml_el, \
                                 nexson_frag_write_newick
from peyotl import OTULabelStyleEnum
from peyotl import write_as_json, read_as_json
from peyotl.ott import OTT
from peyotl import get_logger
from collections import defaultdict
import sys
import os
_SCRIPT_NAME = os.path.split(sys.argv[0])[-1]
_LOG = get_logger(__name__)
_VERBOSE = True
def debug(msg):
    if _VERBOSE:
        sys.stderr.write('{}: {}\n'.format(_SCRIPT_NAME, msg))
def error(msg):
    sys.stderr.write('{}: {}\n'.format(_SCRIPT_NAME, msg))

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

def group_and_sort_leaves_by_ott_id(tree, edge_by_target, edge_by_source, node_by_id, otus):
    '''returns a dict mapping ott_id to list of elements referring to leafs mapped
    to that ott_id. They keys will be ott_ids and None (for unmapped tips). The values
    are lists of tuples. Each tuple represents a different leaf and contains:
        (integer_for_of_is_examplar: -1 if the node is flagged by ^ot:isTaxonExemplar. 0 otherwise
        the leaf's node_id,
        the node object
        the otu object for the node
        )
    Side effects:
      - adds an @id element to each node object in tree['nodeById']
    '''
    ott_id_to_sortable_list = defaultdict(list)
    leaf_ott_ids = set()
    has_an_exemplar_spec = set()
    for node_id in edge_by_target.keys():
        node_obj = node_by_id[node_id]
        node_obj['@id'] = node_id
        if node_id in edge_by_source:
            continue
        otu_id = node_obj['@otu']
        otu_obj = otus[otu_id]
        ott_id = otu_obj.get('^ot:ottId')
        is_exemplar = node_obj.get('^ot:isTaxonExemplar', False)
        int_is_exemplar = 0
        if is_exemplar:
            has_an_exemplar_spec.add(node_id)
            int_is_exemplar = -1 # to sort to the front of the list
        sortable_el = (int_is_exemplar, node_id, node_obj, otu_obj)
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
    #ebtk = list(edge_by_target.keys()); ebtk.sort(); _LOG.debug('suppress_deg_one_node {} ebt keys = {}'.format(nd_id, ebtk))
    del edge_by_source[par][to_par_edge_id]
    del edge_by_target[nd_id]
    del edge_by_source[nd_id]
    edge_by_source[par][to_child_edge_id] = to_child_edge
    to_child_edge['@source'] = par

class EmptyTreeError(Exception):
    pass

def prune_deg_one_root(tree, edge_by_target, edge_by_source, orphaned_root, nodes_deleted, edges_deleted):
    new_root = orphaned_root
    ebs_el = edge_by_source[new_root]
    while len(ebs_el) == 1:
        edge = ebs_el.values()[0]
        del edge_by_source[new_root]
        nodes_deleted.append(new_root)
        #ebtk = list(edge_by_target.keys()); ebtk.sort(); _LOG.debug('prune_deg_one_root {} ebt keys = {}'.format(new_root, ebtk))
        new_root = edge['@target']
        del edge_by_target[new_root]
        edges_deleted.append(edge['@id'])
        ebs_el = edge_by_source.get(new_root)
        if ebs_el == None:
            raise EmptyTreeError();
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
                        #ebtk = list(edge_by_target.keys()); ebtk.sort(); _LOG.debug('prune_if_deg_too_low {} ebt keys = {}'.format(nd_id, ebtk))
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
        #ebtk = list(edge_by_target.keys()); ebtk.sort(); _LOG.debug('prune_tips {} ebt keys = {}'.format(leaf_id, ebtk))
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
                             to_prune_fsi_set,
                             log_obj):
    '''
    '''
    tree, otus = find_tree_and_otus_in_nexson(nexson, tree_id)
    if tree is None:
        raise KeyError('Tree "{}" was not found.'.format(tree_id))
    edge_by_target = to_edge_by_target_id(tree)
    edge_by_source = tree['edgeBySourceId']
    ingroup_node = prune_ingroup(tree, edge_by_target, edge_by_source, log_obj)
    node_by_id = tree['nodeById']
    node_by_id[ingroup_node]['@id'] = ingroup_node
    by_ott_id = group_and_sort_leaves_by_ott_id(tree, edge_by_target, edge_by_source, node_by_id, otus)
    revised_ingroup_node = ingroup_node
    #ebtk = list(edge_by_target.keys()); ebtk.sort(); _LOG.debug('prune_tree_for_supertree ebt keys = {}'.format(ebtk))
    # Leaf nodes with no OTT ID at all...
    if None in by_ott_id:
        nr = prune_tips(tree, edge_by_target, edge_by_source, by_ott_id[None], 'unmapped_otu', log_obj)
        del by_ott_id[None]
        if nr is not None:
            revised_ingroup_node = nr
    # Check the stored OTT Ids against the current version of OTT
    mapped, unrecog, forward2unrecog, pruned, old2new = ott.map_ott_ids(by_ott_id.keys(), to_prune_fsi_set)
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
    to_retain = []
    for ott_id in by_ott_id:
        if ott_id in lost_tips:
            continue
        n = old2new.get(ott_id)
        if n is None:
            n = ott_id
        nd = ott_tree.find_node(n)
        assert nd is not None
        if nd.children:
            # nd must be an internal node.
            #   given that the descendants of this node are mapped in a more specific
            #   way, we will prune this ott_id from the tree
            taxon_contains_other_ott_ids.append(ott_id)
        else:
            to_retain.append(ott_id)
    for ott_id in taxon_contains_other_ott_ids:
        nr = prune_tips(tree, edge_by_target, edge_by_source, by_ott_id[ott_id], 'mapped_to_taxon_containing_other_mapped_tips', log_obj)
        del by_ott_id[ott_id]
        if nr is not None:
            revised_ingroup_node = nr
    # finally, we walk through any ott_id's mapped to multiple nodes
    for ott_id in to_retain:
        nm = by_ott_id[ott_id]
        if len(nm) > 1:
            i, retained_nd_id, n, o = nm.pop(0)
            if i == -1:
                reason = 'replaced_by_exemplar_node'
            else:
                reason = 'replaced_by_arbitrary_node'
            nr = prune_tips(tree, edge_by_target, edge_by_source, by_ott_id[ott_id], reason, log_obj)
            if nr is not None:
                revised_ingroup_node = nr
    if revised_ingroup_node != ingroup_node:
        log_obj['new_ingroup_node'] = revised_ingroup_node
    return revised_ingroup_node, edge_by_source, node_by_id, otus

if __name__ == '__main__':
    import argparse
    import codecs
    import sys
    import os
    description = ''
    parser = argparse.ArgumentParser(prog='to_clean_ott_id_mapped_leaves.py', description=description)
    parser.add_argument('nexson',
                        nargs='*',
                        type=str,
                        help='nexson files with the name pattern studyID_treeID.json')
    parser.add_argument('--input-dir',
                        default=None,
                        type=str,
                        required=False,
                        help='a directory to prepend to the nexson filename or tag')
    parser.add_argument('--nexson-file-tags',
                        default=None,
                        type=str,
                        required=False,
                        help='a filepath to a file that holds the studyID_treeID "tag" for the inputs, one per line. ".json" will be appended to create the filenames.')
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
    parser.add_argument('--ott-prune-flags',
                        default=None,
                        type=str,
                        required=False,
                        help='Optional comma-separated list of flags to prune. If omitted, the treemachine flags are used.')
    parser.add_argument('--input-files-list',
                        default=None,
                        type=str,
                        required=False,
                        help='A list of input NexSON filenames.')
    args = parser.parse_args(sys.argv[1:])
    ott_dir, out_dir = args.ott_dir, args.out_dir
    flags_str = args.ott_prune_flags
    try:
        assert os.path.isdir(args.ott_dir)
    except:
        error('Expecting ott-dir argument to be a directory. Got "{}"'.format(args.ott_dir))
        sys.exit(1)
    if args.nexson:
        inp_files = list(args.nexson)
    else:
        if args.nexson_file_tags:
            with open(os.path.expanduser(args.nexson_file_tags), 'rU') as tf:
                inp_files = ['{}.json'.format(i.strip()) for i in tf if i.strip()]
        elif args.input_files_list:
            with open(os.path.expanduser(args.input_files_list), 'rU') as tf:
                inp_files = [i.strip() for i in tf if i.strip()]
        else:
            error('nexson file must be specified as a positional argument or via the --nexson-file-tags or --input-files-list argument.')
            sys.exit(1)
    if not inp_files:
        error('No input files specified.')
    in_dir = args.input_dir
    if in_dir:
        in_dir = os.path.expanduser(in_dir)
        inp_files = [os.path.join(in_dir, i) for i in inp_files]
    if flags_str is None:
        flags = ott.TREEMACHINE_SUPPRESS_FLAGS
    else:
        flags = flags_str.split(',')
    ott = OTT(ott_dir=args.ott_dir)
    to_prune_fsi_set = ott.convert_flag_string_set_to_union(flags)
    for inp in inp_files:
        sys.stderr.write('{}\n'.format(inp))
        log_obj = {}
        inp_fn = os.path.split(inp)[-1]
        study_tree = '.'.join(inp_fn.split('.')[:-1]) # strip extension
        x = study_tree.split('_')
        if len(x) != 3:
            sys.exit('Currently using the NexSON file name to indicate the tree via: studyID_treeID.json. Expected exactly 2 _ in the filename.\n')
        tree_id = study_tree.split('_')[-1]
        nexson_blob = read_as_json(inp)
        try:
            x = prune_tree_for_supertree(nexson=nexson_blob,
                                         tree_id=tree_id,
                                         ott=ott,
                                         to_prune_fsi_set=to_prune_fsi_set,
                                         log_obj=log_obj)
        except EmptyTreeError:
            log_obj['EMPTY_TREE'] = True
            x = None
        out_log = os.path.join(args.out_dir, study_tree + '.json')
        write_as_json(log_obj, out_log)
        newick_fp = os.path.join(args.out_dir, study_tree + '.tre')
        def compose_label(node, otu):
            try:
                return '_'.join([otu['^ot:ottTaxonName'], str(node['@id']), 'ott' + str(otu['^ot:ottId'])])
            except:
                # internal nodes may lack otu's but we still want the node Ids
                return '_{}_'.format(str(node['@id']))
        with codecs.open(newick_fp, 'w', encoding='utf-8') as outp:
            if x is not None:
                ingroup, edges, nodes, otus = x
                nexson_frag_write_newick(outp,
                                         edges,
                                         nodes,
                                         otus,
                                         label_key=compose_label,
                                         leaf_labels=None,
                                         root_id=ingroup,
                                         ingroup_id=None,
                                         bracket_ingroup=False,
                                         with_edge_lengths=False)
                outp.write('\n')