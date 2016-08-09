#! /usr/bin/env python
# coding=utf-8
from peyotl.amendments.amendments_umbrella import _TaxonomicAmendmentStore
import unittest
from peyotl.test.support import pathmap
import os

from peyotl.utility import get_logger
_LOG = get_logger(__name__)

_repos = pathmap.get_test_repos()
mc = _repos['mini_amendments']

@unittest.skipIf(not os.path.isdir(mc),
                 'Peyotl not configured for maintainer test of mini_amendments.' \
                 'Skipping this test is normal (for everyone other than maintainers).\n' \
                 'See http://opentreeoflife.github.io/peyotl/maintainer/')

class TestTaxonomicAmendments(unittest.TestCase):
    def setUp(self):
        self.r = dict(_repos)

    def testInit(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        self.assertEqual(1, len(c._shards))
    def testAmendmentIndexing(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        k = list(c._doc2shard_map.keys())
        k.sort()
        expected = ['additions-5000000-5000003']
        # TODO: populate with more test data?
        self.assertEqual(k, expected)
    def testURL(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        self.assertTrue(c.get_public_url('additions-5000000-5000003').endswith('-5000003.json'))  # TODO
    def testAmendmentIds(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        k = list(c.get_doc_ids())
        k.sort()
        expected = ['additions-5000000-5000003']  # TODO: add more docs, to test sorting?
        self.assertEqual(k, expected)
    ## Is there a safer way to test ottid-minting, without making "counterfeit" ids?
    # def testNextOTTId(self):
    #     c = _TaxonomicAmendmentStore(repos_dict=self.r)
    #     mf = c._growing_shard._id_minting_file
    #     noi = p._mint_new_ott_ids(how_many=3)
    #     self.assertEqual(noi + 3, read_as_json(mf)['next_ott_id'])
    def testAmendmentCreation(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        # TODO: create a new amendment with a unique name, confirm it exists AND has the expected id.
    def testNewAmendmentIds(self):
        # We assign each new 'additions' amendment a unique id based on the
        # range of minted ottids.
        # TODO: Determine behavior for other subtypes
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        # TODO: create a new amendment with a specified range of ottids
    def testAmendmentDeletion(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        # TODO: create a new amendment with a unique name, confirm it exists
        # TODO: delete the amendment, make sure it's gone
    def testChangedAmendments(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        c.pull()  # get the full git history
        # this SHA only affected other files (not docs)
        changed = c.get_changed_docs('1660edb50e2cf5e4e8a09225260cde52ee80ed45')
        self.assertEqual(set(), changed)
        # check for known changed amendments in this repo (ignoring other changed files)
        changed = c.get_changed_docs('59e6d2d2ea62aa1ce784d29bdd43e74aa80d07d4')
        self.assertEqual(set([u'additions-5000000-5000003.json']), changed)
        # check a doc that changed (against whitelist)
        changed = c.get_changed_docs('59e6d2d2ea62aa1ce784d29bdd43e74aa80d07d4',
                                     [u'additions-5000000-5000003.json'])
        self.assertEqual(set([u'additions-5000000-5000003.json']), changed)
        # checking a bogus doc id should work, but find nothing
        changed = c.get_changed_docs('59e6d2d2ea62aa1ce784d29bdd43e74aa80d07d4',
                                     [u'non-existing-amendment.json'])
        self.assertEqual(set(), changed)
        # passing a foreign (or nonsense) SHA should raise a ValueError
        self.assertRaises(ValueError, c.get_changed_docs, 'bogus-SHA')

if __name__ == "__main__":
    unittest.main(verbosity=5)
