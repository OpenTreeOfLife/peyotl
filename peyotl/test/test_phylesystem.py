#! /usr/bin/env python
from peyotl.utility.input_output import read_as_json
from peyotl.phylesystem.phylesystem_umbrella import _Phylesystem
import unittest
from peyotl.test.support import pathmap
import os
_repos = pathmap.get_test_repos()
ms, mp = _repos['mini_system'], _repos['mini_phyl']

#pylint: disable=W0212
@unittest.skipIf((not os.path.isdir(ms)) or (not os.path.isdir(mp)),
                 'Peyotl not configured for maintainer test of mini_phyl/system.' \
                 'Skipping this test is normal (for everyone other than MTH and EJBM).\n' \
                 'See http://opentreeoflife.github.io/peyotl/maintainer/ ')
class TestPhylesystem(unittest.TestCase):
    def setUp(self):
        self.r = dict(_repos)
    def testInit(self):
        p = _Phylesystem(repos_dict=self.r)
        self.assertEqual(2, len(p._shards))
    def testStudyIndexing(self):
        p = _Phylesystem(repos_dict=self.r)
        k = list(p._doc2shard_map.keys())
        k.sort()
        self.assertEqual(k, ['xy_10', 'xy_13', 'zz_11', 'zz_112'])
    def testURL(self):
        p = _Phylesystem(repos_dict=self.r)
        self.assertTrue(p.get_public_url('xy_10').endswith('xy_10.json'))
        self.assertTrue(p.get_public_url('zz_112').endswith('zz_112.json'))
    def testStudyIds(self):
        p = _Phylesystem(repos_dict=self.r)
        k = list(p.get_study_ids())
        k.sort()
        self.assertEqual(k, ['xy_10', 'xy_13', 'zz_11', 'zz_112'])
    def testNextStudyIds(self):
        p = _Phylesystem(repos_dict=self.r)
        mf = p._growing_shard._id_minting_file
        nsi = p._mint_new_study_id()
        self.assertEqual(int(nsi.split('_')[-1]) + 1, read_as_json(mf)['next_study_id'])
        self.assertTrue(nsi.startswith('zz_'))
    def testChangedStudies(self):
        p = _Phylesystem(repos_dict=self.r)
        changed = p.get_changed_studies('2d59ab892ddb3d09d4b18c91470b8c1c4cca86dc')
        self.assertEqual(set(['xy_13', 'xy_10']), changed)
        changed = p.get_changed_studies('2d59ab892ddb3d09d4b18c91470b8c1c4cca86dc', ['zz_11'])
        self.assertEqual(set(), changed)
        changed = p.get_changed_studies('2d59ab892ddb3d09d4b18c91470b8c1c4cca86dc', ['zz_112'])
        self.assertEqual(set(), changed)
        self.assertRaises(ValueError, p.get_changed_studies, 'bogus')


if __name__ == "__main__":
    unittest.main(verbosity=5)
