#! /usr/bin/env python
from peyotl.nexson_syntax import read_as_json
from peyotl.phylesystem.phylesystem_umbrella import _Phylesystem
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
        mf = p._growing_shard._id_minting_file
        nsi = p._mint_new_study_id()
        self.assertEqual(int(nsi.split('_')[-1]) + 1, read_as_json(mf)['next_study_id'])
        self.assertTrue(nsi.startswith('ot_'))
        r = _Phylesystem(repos_dict=self.r, new_study_prefix='ab_')
        mf = r._growing_shard._id_minting_file
        nsi = r._mint_new_study_id()
        self.assertTrue(nsi.startswith('ab_'))
        self.assertEqual(int(nsi.split('_')[-1]) + 1, read_as_json(mf)['next_study_id'])

    def testChangedStudies(self):
        p = _Phylesystem(repos_dict=self.r)
        changed = p.get_changed_studies('aa8964b55bfa930a91af7a436f55f0acdc94b918')
        self.assertEqual(set('9'), changed)
        changed = p.get_changed_studies('aa8964b55bfa930a91af7a436f55f0acdc94b918', ['10'])
        self.assertEqual(set(), changed)
        self.assertRaises(ValueError, p.get_changed_studies, 'bogus')


if __name__ == "__main__":
    unittest.main(verbosity=5)
