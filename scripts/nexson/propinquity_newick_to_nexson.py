#!/usr/bin/env python
from peyotl.phylo.tree import parse_newick
from peyotl.nexson_syntax import get_empty_nexson
from peyotl import write_as_json
import codecs
import json
import sys
import os
import re
_ID_EXTRACTOR = re.compile(r'^.*[^0-9]([0-9]+)$')
_ALL_DIGIT_ID_EXTRACTOR = re.compile(r'^([0-9]+)$')
def ott_id_from_label(s):
    x = _ID_EXTRACTOR.match(s)
    if not x:
        x = _ALL_DIGIT_ID_EXTRACTOR.match(s)
        if not x:
            raise RuntimeError('Expecting each tip label to end in an integer. Found "{}"'.format(s))
    return int(x.group(1))
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
    pyid2int = {}
    curr_nd_counter = 1
    with codecs.open(args.newick, 'r', encoding='utf8') as inp:
        tree = parse_newick(stream=inp)
        nexson = get_empty_nexson()
        body = nexson['nexml']
        otus = body['otusById'].values()[0]['otuById']
        ntree = body['treesById'].values()[0]['treeById']
        ebsi, nbi = {}, {}
        ntree['edgeBySourceId'] = ebsi
        ntree['nodeById'] = nbi
        for node in tree._root.preorder_iter():
            nid = id(node)
            i = pyid2int.get(nid)
            if i is None:
                i = curr_nd_counter
                curr_nd_counter += 1
                pyid2int[nid] = i
            node_id_s = 'node{}'.format(i)
            otu_id_s = 'otu{}'.format(i)
            n_obj = nbi.setdefault(node_id_s, {})
            if node is tree._root:
                n_obj['@root'] = True
            else:
                edge_id_s = 'edge{}'.format(i)
                pid = id(node.parent)
                pni = 'node{}'.format(pyid2int[pid])
                ed = ebsi.setdefault(pni, {})
                ed[edge_id_s] = {'@source': pni, '@target': node_id_s}
            if not node.children:
                n_obj['@otu'] = otu_id_s
                orig = node._id
                ott_id = ott_id_from_label(orig)
                otus[otu_id_s] = {"^ot:originalLabel": orig, "^ot:ottId": ott_id}
        write_as_json(nexson, out)

if __name__ == '__main__':
    _main()
