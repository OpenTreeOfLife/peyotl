#! /usr/bin/env python
# coding=utf-8
import unittest

from peyotl.amendments.amendments_umbrella import _TaxonomicAmendmentStore
from peyotl.test.support import pathmap
from peyotl.utility import get_logger

_LOG = get_logger(__name__)

test_repos = pathmap.get_test_repos(['mini_amendments'])


@unittest.skipIf(not test_repos,
                 'See the documentation about the maintainers test to configure your '
                 'machine to run tests that require the mini_amendments repos')
class TestTaxonomicAmendments(unittest.TestCase):
    def setUp(self):
        self.c = _TaxonomicAmendmentStore(repos_dict=dict(test_repos))

    def testInit(self):
        self.assertEqual(1, len(self.c._shards))

    def testAmendmentIndexing(self):
        k = list(self.c._doc2shard_map.keys())
        k.sort()
        expected = ['additions-5000000-5000003']
        # TODO: populate with more test data?
        self.assertEqual(k, expected)

    def testURL(self):
        self.assertTrue(self.c.get_public_url('additions-5000000-5000003').endswith('-5000003.json'))  # TODO

    def testAmendmentIds(self):
        k = list(self.c.get_doc_ids())
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
        # TODO: create a new amendment with a unique name, confirm it exists AND has the expected id.
        pass

    def testNewAmendmentIds(self):
        # We assign each new 'additions' amendment a unique id based on the
        # range of minted ottids.
        # TODO: Determine behavior for other subtypes
        # TODO: create a new amendment with a specified range of ottids
        pass

    def testChangedAmendments(self):
        self.c.pull()  # get the full git history
        # this SHA only affected other files (not docs)
        # REMINDER: This will list all changed files *since* the stated SHA; results
        # will probably change if more work is done in the mini_amendments repo!
        # TODO: add a test with the HEAD commit SHA that should get no changes
        # check for known changed amendments in this repo (ignoring other changed files)
        changed = self.c.get_changed_docs('59e6d2d2ea62aa1ce784d29bdd43e74aa80d07d4')
        self.assertEqual({u'additions-5000000-5000003.json'}, changed)
        # check a doc that changed (against whitelist)
        changed = self.c.get_changed_docs('59e6d2d2ea62aa1ce784d29bdd43e74aa80d07d4',
                                          [u'additions-5000000-5000003.json'])
        self.assertEqual({u'additions-5000000-5000003.json'}, changed)
        # checking a bogus doc id should work, but find nothing
        changed = self.c.get_changed_docs('59e6d2d2ea62aa1ce784d29bdd43e74aa80d07d4',
                                          [u'non-existing-amendment.json'])
        self.assertEqual(set(), changed)
        # passing a foreign (or nonsense) SHA should raise a ValueError
        self.assertRaises(ValueError, self.c.get_changed_docs, 'bogus-SHA')


if __name__ == "__main__":
    unittest.main(verbosity=5)
