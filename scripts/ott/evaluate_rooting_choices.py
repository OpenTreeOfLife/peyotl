#!/usr/bin/env python
from peyotl.manip import NexsonTreeProxy
from peyotl.ott import OTT
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
        preorder_list = []
        ott_ids = []
        for el in tree_proxy:
            preorder_list.append(el)
            node_id, node, edgeid, edge = el
            if edge is not None:
                assert node_id == edge['@target']
            if tree_proxy.is_leaf(node_id):
                ott_id = tree_proxy.get_ott_id(node)
                if ott_id is not None:
                    ott_ids.append(ott_id)
        taxo_tree = ott.induced_tree(ott_ids)
        taxo_tree.write_newick(sys.stdout)

