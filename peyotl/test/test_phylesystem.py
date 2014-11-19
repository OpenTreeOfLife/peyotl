#! /usr/bin/env python
from peyotl.phylesystem import _Phylesystem
import unittest
from peyotl.test.support import pathmap
import os
_repos = pathmap.get_test_repos()
ms, mp = _repos['mini_system'], _repos['mini_phyl']

#pylint: disable=W0212
@unittest.skipIf((not os.path.isdir(ms)) or (not os.path.isdir(mp)),
                 'Peyotl not configured for maintainer test of mini_phyl/system.' \
                 'Skipping this test is normal (for everyone other than MTH and EJBM).')
class TestPhylesystem(unittest.TestCase):
    def setUp(self):
        self.r = dict(_repos)
        #print(self.r)
    def testInit(self):
        p = _Phylesystem(repos_dict=self.r)
        self.assertEqual(2, len(p._shards))
    def testStudyIndexing(self):
        p = _Phylesystem(repos_dict=self.r)
        k = list(p._study2shard_map.keys())
        k.sort()
        self.assertEqual(k, ['10', '11', '12', '9'])
    def testURL(self):
        p = _Phylesystem(repos_dict=self.r)
        self.assertTrue(p.get_public_url('9').endswith('9.json'))
    def testStudyIds(self):
        p = _Phylesystem(repos_dict=self.r)
        k = list(p.get_study_ids())
        k.sort()
        self.assertEqual(k, ['10', '11', '12', '9'])
    def testNextStudyIds(self):
        p = _Phylesystem(repos_dict=self.r)
        nsi = p._mint_new_study_id()
        self.assertTrue(nsi.startswith('ot_'))
        r = _Phylesystem(repos_dict=self.r, new_study_prefix='ab_')
        nsi = r._mint_new_study_id()
        self.assertTrue(nsi.startswith('ab_'))


if __name__ == "__main__":
    unittest.main(verbosity=5)
