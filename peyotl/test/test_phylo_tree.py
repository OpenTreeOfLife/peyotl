#! /usr/bin/env python
from peyotl.phylo.tree import create_tree_from_id2par
from peyotl.utility import get_logger
import unittest
_bogus_id2par = {'h': 'hp',
                 'p': 'hp',
                 'g': 'hpg',
                 'hp': 'hpg',
                 'hpg': 'hpgPo',
                 'Po': 'hpgPo',
                 'Hy': 'HySyHoNo',
                 'Sy': 'HySyHoNo',
                 'Ho': 'HySyHoNo',
                 'No': 'HySyHoNo',
                 'HySyHoNo': 'hpgPoHySyHoNo',
                 'hpgPoHySyHoNo': None,
                 'hpgPo': 'hpgPoHySyHoNo',
                 'bogus_tip': 'bogus_internal',
                 'bogus_internal': 'bogus_i2',
                 'bogus_i2': 'bogus_i3',
                 'bogus_i3': 'bogus_i4',
                 'bogus_i4': 'bogus_i5',
                 'bogus_i5': 'bogus_i6',
                 'bogus_i6': 'bogus_root',
                 'bogus_root': None
                }
_LOG = get_logger(__name__)
class TestPhyloTree(unittest.TestCase):
    def testLengthenEdge(self):
        tree = create_tree_from_id2par(_bogus_id2par, ['hp', 'g', 'h'], create_monotypic_nodes=True)
        self.assertEqual(tree.find_node('hp')._id, 'hp')
        li = tree.leaf_ids
        li.sort()
        self.assertEqual(li, ['g', 'h'])
        tree.do_full_check_of_invariants(self, id2par=_bogus_id2par)

    def testSingleton(self):
        tree = create_tree_from_id2par(_bogus_id2par, ['h'])
        self.assertEqual(tree.find_node('h')._id, 'h')
        tree.do_full_check_of_invariants(self, id2par=_bogus_id2par)
    def testEmpty(self):
        # not sure whether we should return an empty tree, None, or raise an exception...
        self.assertEqual(None, create_tree_from_id2par(_bogus_id2par, []))
    def testInsertAnc(self):
        pass
    def testCherry(self):
        tree = create_tree_from_id2par(_bogus_id2par, ['h', 'p'])
        self.assertTrue(tree._root._id == 'hp')
        self.assertEqual(len(tree.leaves), 2)
        i = tree.postorder_node_iter()
        self.assertTrue(next(i)._id in ['h', 'p'])
        self.assertTrue(next(i)._id in ['h', 'p'])
        self.assertEqual(next(i)._id, 'hp')
        self.assertRaises(StopIteration, next, i)
        self.assertRaises(ValueError, create_tree_from_id2par, _bogus_id2par, ['h', 'bogus_tip'])
        tree.do_full_check_of_invariants(self, id2par=_bogus_id2par)
    def testFullExample(self):
        tips = ['h', 'p', 'g', 'Po', 'Hy', 'Sy', 'Ho', 'No']
        tree = create_tree_from_id2par(_bogus_id2par, tips)
        tree.do_full_check_of_invariants(self, id2par=_bogus_id2par)
if __name__ == "__main__":
    unittest.main()
