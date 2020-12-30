#!/usr/bin/env python
import codecs
import os
import re
import sys

from peyotl import write_as_json
from peyotl.nexson_syntax import get_empty_nexson
from peyotl.phylo.tree import parse_newick

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
    parser.add_argument("-i", "--ids",
                        required=True,
                        help="comma separated list of tree IDs to be assigned to the trees in the newick file.")
    parser.add_argument('newick', help='filepath of the newick tree')
    args = parser.parse_args()
    if not os.path.exists(args.newick):
        sys.exit('The file "{}" does not exist'.format(args.newick))
    tree_id_list = args.ids.split(',')
    if not tree_id_list:
        sys.exit('At least one tree ID must be provided')
    tree_id_it = iter(tree_id_list)
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        out = sys.stdout
    except:
        out = codecs.getwriter('utf-8')(sys.stdout)
    pyid2int = {}
    curr_nd_counter = 1
    # sys.stderr.write('args.newick= {}\n'.format(args.newick))
    with codecs.open(args.newick, 'r', encoding='utf8') as inp:
        tree = parse_newick(stream=inp)
<<<<<<< HEAD
=======
        # sys.stderr.write('tree = {}\n'.format(tree))
>>>>>>> origin/allow-subtree-of-taxonomy
        tree_id = next(tree_id_it)
        nexson = get_empty_nexson()
        body = nexson['nexml']
        all_otus_groups = list(body['otusById'].values())
        assert len(all_otus_groups) == 1
        # sys.stderr.write('all_otus_groups = {}\n'.format(all_otus_groups))
        first_otus_group = all_otus_groups[0]
        all_trees_groups = list(body['treesById'].values())
        assert len(all_trees_groups) == 1
        first_trees_group = all_trees_groups[0]
        first_trees_group['^ot:treeElementOrder'].append(tree_id)
        otus = first_otus_group['otuById']
        all_trees_dict = first_trees_group['treeById']
        ntree = all_trees_dict.setdefault(tree_id, {})
        ebsi, nbi = {}, {}
        ntree['edgeBySourceId'] = ebsi
        ntree['nodeById'] = nbi
        root_node_id = None
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
                root_node_id = node_id_s
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
                otus[otu_id_s] = {"^ot:originalLabel": str(orig),
                                  "^ot:ottId": ott_id,
                                  "^ot:ottTaxonName": str(orig)}
        assert root_node_id is not None
        ntree['^ot:rootNodeId'] = str(root_node_id)
        write_as_json(nexson, out)


if __name__ == '__main__':
    _main()
