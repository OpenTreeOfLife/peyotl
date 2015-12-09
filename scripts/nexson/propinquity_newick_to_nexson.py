#!/usr/bin/env python
from peyotl.phylo.tree import parse_newick

def _main():
    import sys, os, codecs, json
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
    with codecs.open(args.newick, 'r', encoding='utf8') as inp:
        tree = parse_newick(stream=inp)
        print tree.leaf_ids

if __name__ == '__main__':
    _main()
