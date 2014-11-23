#! /usr/bin/env python
from peyotl.phylo.tree import TreeWithPathsInEdges, create_tree_from_id2par
from peyotl.utility import get_logger
import unittest
_bogus_id2par = {'h': 'hp',
                 'p': 'hp',
                 'g': 'hpg',
                 'hp': 'hpg',
                 'hpg': 'hpgPo',
                 'Po': 'hpgPo',
                 'Hy': 'HySi',
                 'Si': 'HySi',
                 'HySi': 'hpgPoHySi',
                 'hpgPo': 'hpgPoHySi',
                 'bogus_tip': 'bogus_internal',
                 'bogus_internal': 'bogus_i2',
                 'bogus_i3': 'bogus_i4',
                 'bogus_i4': 'bogus_i5',
                 'bogus_i5': 'bogus_i6',
                 'bogus_i6': 'bogus_root', }
_LOG = get_logger(__name__)
class TestPhyloTree(unittest.TestCase):
    def testCherry(self):
        tree = create_tree_from_id2par(_bogus_id2par, ['h', 'p'])
        self.assertTrue(tree._root._id == 'hp')
        self.assertEqual(len(tree.leaves), 2)
        i = tree.postorder_node_iter()
        self.assertTrue(i.next()._id in ['h', 'p'])
        self.assertTrue(i.next()._id in ['h', 'p'])
        self.assertEqual(i.next()._id, 'hp')
        self.assertRaises(StopIteration, i.next)
        tree = create_tree_from_id2par(_bogus_id2par, ['h', 'bogus_tip'])



if __name__ == "__main__":
    unittest.main()
