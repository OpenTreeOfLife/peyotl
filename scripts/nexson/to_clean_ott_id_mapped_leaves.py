#!/usr/bin/env python
from peyotl.nexson_syntax import extract_tree_nexson, get_nexml_el
from peyotl import OTULabelStyleEnum
from peyotl import write_as_json, read_as_json
from peyotl.ott import OTT
from collections import defaultdict
_VERBOSE = True
def debug(msg):
    if _VERBOSE:
        sys.stderr.write(msg)
        sys.stderr.write('\n')

def to_edge_by_target_id(tree):
    ebt = {}
    ebs = tree['edgeBySourceId']
    for edge_dict in ebs.values():
        for edge_id, edge in edge_dict.items():
            target_id = edge['@target']
            edge['@id'] = edge_id
            assert target_id not in ebt
            ebt[target_id] = edge
    check_rev_dict(tree, ebt)
    return ebt

def check_rev_dict(tree, ebt):
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
    Caller must delete the edge to node_id'''
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
    

def prune_to_ingroup(edge_by_target, edge_by_source, ingroup_node, log_obj):
    edge_to_del = edge_by_target.get(ingroup_node)
    if edge_to_del is None:
        return
    nodes_deleted = []
    edges_deleted = []
    prune_edge_and_below(edge_by_target, edge_by_source, edge_to_del, nodes_deleted, edges_deleted)
    log_obj['outgroup'] = {'nodes': nodes_deleted, 'edges': edges_deleted}

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

if __name__ == '__main__':
    import argparse
    import codecs
    import sys
    import os
    description = ''
    parser = argparse.ArgumentParser(prog='suppress-dubious', description=description)
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
    for inp in args.nexson:
        log_obj = {}
        study_tree = '.'.join(inp.split('.')[:-1]) # strip extension
        tree_id = study_tree.split('_')[-1]
        blob = read_as_json(inp)
        tree, otus = find_tree_and_otus_in_nexson(blob, tree_id)
        assert tree is not None
        edge_by_target = to_edge_by_target_id(tree)
        edge_by_source = tree['edgeBySourceId']

        # Prune to just the ingroup
        ingroup_node = tree.get('^ot:rootNodeId')
        if ingroup_node is None:
            debug('No ingroup node specified.')
        elif ingroup_node != tree['^ot:rootNodeId']:
            prune_to_ingroup(edge_by_target, edge_by_source, ingroup_node, log_obj)
        else:
            debug('Ingroup node is root.')
        
        leaves = [i for i in edge_by_target.keys() if i not in edge_by_source]
        ott_id_to_sortable_list = defaultdict(list)
        leaf_ott_ids = set()
        has_an_exemplar_spec = set()
        for leaf_id in leaves:
            node_obj = tree['nodeById'][leaf_id]
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
            print v
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
    sys.exit(0)
    ott = OTT(ott_dir=args.ott_dir)
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
