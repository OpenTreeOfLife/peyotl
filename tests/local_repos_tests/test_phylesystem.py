#! /usr/bin/env python

# put tests here that use local phylesystem
# see http://opentreeoflife.github.io/peyotl/maintainer/ for setup

from peyotl.utility.input_output import read_as_json
from peyotl.phylesystem.phylesystem_umbrella import _Phylesystem
import unittest
from peyotl.test.support import pathmap
import os

from peyotl.utility import get_logger

_LOG = get_logger(__name__)

_repos = pathmap.get_test_repos()
ms, mp = _repos['mini_system'], _repos['mini_phyl']


# TODO: filter repo list to just phylesystem shards? or rely on smart (failed) shard creation?
# _repos = {s: _repos[s] for s in _repos if s in ('mini_system', 'mini_phyl',)}

# pylint: disable=W0212
@unittest.skipIf((not os.path.isdir(ms)) or (not os.path.isdir(mp)),
                 'Peyotl not configured for maintainer test of mini_phyl/system.'
                 'Skipping this test is normal (for everyone other than MTH and EJBM).\n'
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
        p.pull()  # get the full git history
        changed = p.get_changed_studies('5f50b669cb4867d39e9a85e7fd1e2aa8e9a3242b')
        self.assertEqual({'xy_13', 'xy_10'}, changed)
        changed = p.get_changed_studies('5f50b669cb4867d39e9a85e7fd1e2aa8e9a3242b', ['zz_11'])
        self.assertEqual(set(), changed)
        changed = p.get_changed_studies('5f50b669cb4867d39e9a85e7fd1e2aa8e9a3242b', ['zz_112'])
        self.assertEqual(set(), changed)
        self.assertRaises(ValueError, p.get_changed_studies, 'bogus')

    def testIterateStudies(self):
        p = _Phylesystem(repos_dict=self.r)
        k = list(p.get_study_ids())
        count = 0
        for study_id, file_path in p.iter_study_filepaths():
            count += 1
        self.assertEqual(count, len(k))
        count = 0
        for study_id, n in p.iter_study_objs():
            count += 1
        self.assertEqual(count, len(k))


if __name__ == "__main__":
    unittest.main(verbosity=5)
