#!/usr/bin/env python
# Example of getting trees from a collection, and properties for those
# trees and studies
# Specifically, prints properties important for synthesis for trees in a
# collection

from __future__ import print_function
from peyotl.api import PhylesystemAPI
from peyotl import collection_to_included_trees, read_as_json
from peyotl.nexson_syntax import get_nexml_el
from peyotl.nexson_proxy import NexsonProxy

if __name__ == '__main__':
    import argparse
    import codecs
    import sys
    import os
    description = 'Takes an collection JSON and prints out information from it'
    parser = argparse.ArgumentParser(prog='collection_stats.py', description=description)
    parser.add_argument('collection',
                        default=None,
                        type=str,
                        help='filepath for the collections JSON')
    args = parser.parse_args(sys.argv[1:])
    if not os.path.isfile(args.collection):
        sys.exit('Input collection "{}" does not exist.\n'.format(args.collection))
    try:
        # get the list of trees that are 'included'
        included = collection_to_included_trees(args.collection)
    except:
        sys.stderr.write('JSON parse error when reading collection "{}".\n'.format(args.collection))
        raise

    # work off the local copy of the phylesystem
    phy = PhylesystemAPI(get_from='local')

    # looking for the tree properties: ot:unrootedTree, ot:inGroupClade
    # and the study property ot:candidateTreeForSynthesis
    print("studyid,treeid,preferred,ingroup,unrooted")
    for d in included:
        studyid = d['studyID']
        treeid = d['treeID']

        # expect these defaults for synthesis trees
        unrootedTree = False
        ingroupSpecified = True
        preferredTree = True
        check = True

        nx = phy.get_study(studyid)['data']
        np = NexsonProxy(nexson=nx)
        candidateTreeList = np._nexml_el['^ot:candidateTreeForSynthesis']
        if not treeid in candidateTreeList:
            preferredTree = False
            check = False
        tree = np.get_tree(treeid)
        if tree['^ot:inGroupClade'] == "":
            ingroupSpecified = False
            check = False
        if tree['^ot:unrootedTree']:
            unrootedTree = True
            check = False

        if not check:
            print("{s},{t},{p},{i},{r}").format(
                s = studyid,
                t = treeid,
                p = preferredTree,
                i = ingroupSpecified,
                r = unrootedTree
                )
