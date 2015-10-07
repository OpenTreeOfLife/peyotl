#!/usr/bin/env python
from peyotl.nexson_syntax import extract_tree_nexson, get_nexml_el
from peyotl import OTULabelStyleEnum
from peyotl import write_as_json, read_as_json
from peyotl.ott import OTT
from collections import defaultdict

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
        
        print ingroup_node
        print tree.keys()
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
