#! /usr/bin/env python
from peyotl.nexson_proxy import NexsonProxy
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)
class TestProxy(unittest.TestCase):
    def setUp(self):
        blob = pathmap.nexson_obj('9/v1.2.json')
        self.np = NexsonProxy(nexson=blob)
    def testGetters(self):
        self.assertIs(self.np.get_tree('bogus'), None)
        self.assertIsNot(self.np.get_tree('tree1'), None)
        self.assertIs(self.np.get_tree('otu123'), None)
        self.assertIs(self.np.get_otu('bogus'), None)
        self.assertIs(self.np.get_otu('tree1'), None)
        self.assertIsNot(self.np.get_otu('otu123'), None)
    def testCaching(self):
        f = self.np.get_tree('tree1')
        s = self.np.get_tree('tree1')
        self.assertIs(f, s)
        fn = f.get_node('node247')
        sn = s.get_node('node247')
        self.assertIs(fn, sn)
        fo = self.np.get_otu('otu123')
        so = sn.otu
        self.assertIs(fo, so)
    def testTreeIter(self):
        ntp = self.np.get_tree('tree1')
        nbi = ntp['nodeById']
        ebi = ntp['edgeBySourceId']
        ks = set(nbi.keys())
        its = set()
        edge_less = None
        for node in ntp:
            its.add(node.node_id)
            self.assertIs(node.node, nbi[node.node_id])
            if node.edge is None:
                self.assertIs(edge_less, None)
                edge_less = node.node_id
            else:
                s = node.edge['@source']
                ed = ebi[s]
                self.assertIs(node.edge, ed[node.edge_id])
        self.assertEqual(ntp['^ot:rootNodeId'], edge_less)
        self.assertEqual(ks, its)
if __name__ == "__main__":
    unittest.main()
