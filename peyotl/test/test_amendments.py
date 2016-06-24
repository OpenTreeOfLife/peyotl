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
        expected = ['TestUserB/fungal-trees', 'TestUserB/my-favorite-trees',
                    'test-user-a/my-favorite-trees', 'test-user-a/trees-about-bees']
        # TODO: populate with test data, use those ids here
        self.assertEqual(k, expected)
    def testURL(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        self.assertTrue(c.get_public_url('TestUserB/fungal-trees').endswith('ngal-trees.json'))  # TODO
    def testAmendmentIds(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        k = list(c.get_doc_ids())
        k.sort()
        expected = ['TestUserB/fungal-trees', 'TestUserB/my-favorite-trees',
                    'test-user-a/my-favorite-trees', 'test-user-a/trees-about-bees']  # TODO
        self.assertEqual(k, expected)
    def testNextOTTId(self):
        c = _TaxonomicAmendmentStore(repos_dict=self.r)
        mf = c._growing_shard._id_minting_file
        noi = p._mint_new_ott_id()
        self.assertEqual(noi + 1, read_as_json(mf)['next_ott_id'])
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
        # check for known changed amendments in this repo
        changed = c.get_changed_docs('637bb5a35f861d84c115e5e6c11030d1ecec92e0')  # TODO
        self.assertEqual(set(), changed)
        changed = c.get_changed_docs('d17e91ae85e829a4dcc0115d5d33bf0dca179247')  # TODO
        self.assertEqual(set([u'TestUserB/fungal-trees.json']), changed)  # TODO
        changed = c.get_changed_docs('af72fb2cc060936c9afce03495ec0ab662a783f6')  # TODO
        expected = set([u'test-user-a/my-favorite-trees.json', u'TestUserB/fungal-trees.json'])  # TODO
        self.assertEqual(expected, changed)
        # check a doc that changed
        changed = c.get_changed_docs('af72fb2cc060936c9afce03495ec0ab662a783f6',
                                     [u'TestUserB/fungal-trees.json'])  # TODO
        self.assertEqual(set([u'TestUserB/fungal-trees.json']), changed)  # TODO
        # check a doc that didn't change
        changed = c.get_changed_docs('d17e91ae85e829a4dcc0115d5d33bf0dca179247',
                                     [u'test-user-a/my-favorite-trees.json'])  # TODO
        self.assertEqual(set(), changed)
        # check a bogus doc id should work, but find nothing
        changed = c.get_changed_docs('d17e91ae85e829a4dcc0115d5d33bf0dca179247',
                                     [u'bogus/fake-trees.json'])  # TODO
        self.assertEqual(set(), changed)
        # passing a foreign (or nonsense) SHA should raise a ValueError
        self.assertRaises(ValueError, c.get_changed_docs, 'bogus')  # TODO

if __name__ == "__main__":
    unittest.main(verbosity=5)
