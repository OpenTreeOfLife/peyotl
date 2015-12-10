#!/usr/bin/env python
from peyotl.phylo.tree import parse_newick
from peyotl.nexson_syntax import get_empty_nexson
from peyotl import write_as_json
import codecs
import json
import sys
import os

def _main():
    import argparse
    _HELP_MESSAGE = '''Takes a filepath to Newick tree file with propinquity-style
leaf labels - unique numeric suffixes which identify the taxon.
Writes a NexSON representation of the tree to
'''

    parser = argparse.ArgumentParser(description=_HELP_MESSAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('newick', help='filepath of the newick tree')
    args = parser.parse_args()
    if not os.path.exists(args.newick):
        sys.exit('The file "{}" does not exist'.format(args.newick))
    out = codecs.getwriter('utf-8')(sys.stdout)
    with codecs.open(args.newick, 'r', encoding='utf8') as inp:
        tree = parse_newick(stream=inp)
        print tree.leaf_ids
        nexson = get_empty_nexson()
        body = nexson['nexml']
        otus, tree = body['otusById'].values()[0]['otuById'], body['treesById'].values()[0]['treeById']
        print otus, tree
        #write_as_json(nexson, out)

if __name__ == '__main__':
    _main()
