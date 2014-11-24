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
    def testCherry(self):
        tree = create_tree_from_id2par(_bogus_id2par, ['h', 'p'])
        self.assertTrue(tree._root._id == 'hp')
        self.assertEqual(len(tree.leaves), 2)
        i = tree.postorder_node_iter()
        self.assertTrue(i.next()._id in ['h', 'p'])
        self.assertTrue(i.next()._id in ['h', 'p'])
        self.assertEqual(i.next()._id, 'hp')
        self.assertRaises(StopIteration, i.next)
        self.assertRaises(ValueError, create_tree_from_id2par, _bogus_id2par, ['h', 'bogus_tip'])
    def testFullExample(self):
        tips = ['h', 'p', 'g', 'Po', 'Hy', 'Sy', 'Ho', 'No']
        tree = create_tree_from_id2par(_bogus_id2par, tips)
        post_order = [nd._id for nd in tree.postorder_node_iter()]
        anc_ref_count = {}
        anc_set = set()
        checked_node = set()
        _LOG.debug('post_order = {}'.format(post_order))
        for t in tips:
            anc_id = _bogus_id2par[t]
            _LOG.debug('anc_id = {}'.format(anc_id))
            anc_ref_count[anc_id] = 1 + anc_ref_count.get(anc_id, 0)
            if anc_ref_count[anc_id] > 1:
                anc_set.add(anc_id)
            self.assertTrue(t in post_order)
            self.assertTrue(anc_id in post_order)
            self.assertTrue(post_order.index(t) < post_order.index(anc_id))
            checked_node.add(t)
        while len(anc_set - checked_node) > 0:
            ns = set()
            for t in anc_set:
                if t in checked_node:
                    continue
                anc_id = _bogus_id2par[t]
                _LOG.debug('anc_id = {}'.format(anc_id))
                anc_ref_count[anc_id] = 1 + anc_ref_count.get(anc_id, 0)
                if anc_ref_count[anc_id] > 1:
                    ns.add(anc_id)
                self.assertTrue(t in post_order)
                checked_node.add(t)
                if anc_id is not None:
                    self.assertTrue(anc_id in post_order)
                    self.assertTrue(post_order.index(t) < post_order.index(anc_id))
            anc_set.update(ns)
            _LOG.debug('anc_set = {}'.format(anc_set))
            _LOG.debug('checked_node = {}'.format(checked_node))

if __name__ == "__main__":
    unittest.main()
