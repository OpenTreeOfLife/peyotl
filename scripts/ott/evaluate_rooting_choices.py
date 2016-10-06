#!/usr/bin/env python
from peyotl.nexson_proxy import NexsonTreeProxy
from peyotl.ott import OTT
from peyotl.evaluate_tree import evaluate_tree_rooting
from enum import Enum


class UnrootedConflictStatus(Enum):
    EQUIVALENT = 0
    INCOMPATIBLE = 1
    RESOLVES = 2  # compatible with "other" tree, and split is not in that tree
    TRIVIAL = 3  # will be compatible with any taxonomy
    NOT_COMPARABLE = 4  # e.g. lacking an OTT ID in a comparison to taxonomy


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
