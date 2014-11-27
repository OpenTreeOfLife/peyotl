#! /usr/bin/env python
from peyotl.nexson_syntax import extract_tree_nexson
from peyotl.manip import NexsonTreeProxy
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)
class TestProxy(unittest.TestCase):
    def setUp(self):
        blob = pathmap.nexson_obj('9/v1.2.json')
        tree_id, tree, otus = extract_tree_nexson(blob, tree_id='tree1')[0]
        self._tree = tree
        self.ntp = NexsonTreeProxy(tree=tree, tree_id=tree_id, otus=otus)
    def testIter(self):
        nbi = self._tree['nodeById']
        ebi = self._tree['edgeBySourceId']
        ks = set(nbi.keys())
        its = set()
        edge_less = None
        for node in self.ntp:
            its.add(node.node_id)
            self.assertIs(node.node, nbi[node.node_id])
            if node.edge is None:
                self.assertIs(edge_less, None)
                edge_less = node.node_id
            else:
                s = node.edge['@source']
                ed = ebi[s]
                self.assertIs(node.edge, ed[node.edge_id])
        self.assertEqual(self._tree['^ot:rootNodeId'], edge_less)
        self.assertEqual(ks, its)
if __name__ == "__main__":
    unittest.main()
