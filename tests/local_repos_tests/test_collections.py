#! /usr/bin/env python
# coding=utf-8
from peyotl.collections_store.collections_umbrella import _TreeCollectionStore
import unittest
from peyotl.test.support import pathmap
import os

from peyotl.utility import get_logger

_LOG = get_logger(__name__)

_repos = pathmap.get_test_repos()
mc = _repos['mini_collections']


# TODO: filter repo list to just tree-collection shards? or rely on smart (failed) shard creation?
# _repos = {'mini_collections': mc}

@unittest.skipIf(not os.path.isdir(mc),
                 'Peyotl not configured for maintainer test of mini_collections.'
                 'Skipping this test is normal (for everyone other than maintainers).\n'
                 'See http://opentreeoflife.github.io/peyotl/maintainer/')
class TestTreeCollections(unittest.TestCase):
    def setUp(self):
        self.r = dict(_repos)

    def testSlugify(self):
        from peyotl.utility.str_util import slugify
        self.assertEqual('simple-test', slugify('Simple Test'))
        self.assertEqual('no-punctuation-allowed', slugify('No punctuation allowed!?'))
        self.assertEqual('no-extra-spaces-', slugify('No \t extra   spaces   '))
        self.assertEqual('untitled', slugify(''))
        self.assertEqual('untitled', slugify('!?'))
        # TODO: allow broader Unicode strings and their capitalization rules?
        # self.assertEqual(u'километр', slugify(u'Километр'))
        self.assertEqual(u'untitled', slugify(u'Километр'))  # no support for now

    def testInit(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        self.assertEqual(1, len(c._shards))

    def testCollectionIndexing(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        k = list(c._doc2shard_map.keys())
        k.sort()
        expected = ['TestUserB/fungal-trees', 'TestUserB/my-favorite-trees',
                    'test-user-a/my-favorite-trees', 'test-user-a/trees-about-bees']
        self.assertEqual(k, expected)

    def testURL(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        self.assertTrue(c.get_public_url('TestUserB/fungal-trees').endswith('ngal-trees.json'))

    def testCollectionIds(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        k = list(c.get_doc_ids())
        k.sort()
        expected = ['TestUserB/fungal-trees', 'TestUserB/my-favorite-trees',
                    'test-user-a/my-favorite-trees', 'test-user-a/trees-about-bees']
        self.assertEqual(k, expected)

    def testCollectionCreation(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        # TODO: create a new collection with a unique name, confirm it exists

    def testCollectionCopying(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        # TODO: copy an existing study under the same user, confirm it's in the right place
        # TODO: copy an existing study under a new user, confirm it's in the right place

    def testNewCollectionIds(self):
        # We assign each new collection a unique id based on the owner's userid +
        # the slugified name, serializing with $NAME-2, etc if this id already exists.
        c = _TreeCollectionStore(repos_dict=self.r)
        # TODO: fetch an existing study, copy to the other user (id should reflect new username)
        # TODO: fetch an existing study, save a copy alongside it (should nudge id via serialization)
        # TODO: create a new study (with the same name) alongside thes (should nudge id via serialization)

    def testCollectionDeletion(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        # TODO: create a new collection with a unique name, confirm it exists
        # TODO: delete the collection, make sure it's gone

    def testChangedCollections(self):
        c = _TreeCollectionStore(repos_dict=self.r)
        c.pull()  # get the full git history
        # check for known changed collections in this repo
        changed = c.get_changed_docs('637bb5a35f861d84c115e5e6c11030d1ecec92e0')
        self.assertEqual({u'TestUserB/fungal-trees.json'}, changed)
        changed = c.get_changed_docs('d17e91ae85e829a4dcc0115d5d33bf0dca179247')
        self.assertEqual({u'TestUserB/fungal-trees.json'}, changed)
        changed = c.get_changed_docs('af72fb2cc060936c9afce03495ec0ab662a783f6')
        expected = {u'test-user-a/my-favorite-trees.json', u'TestUserB/fungal-trees.json'}
        self.assertEqual(expected, changed)
        # check a doc that changed
        changed = c.get_changed_docs('af72fb2cc060936c9afce03495ec0ab662a783f6',
                                     [u'TestUserB/fungal-trees.json'])
        self.assertEqual({u'TestUserB/fungal-trees.json'}, changed)
        # check a doc that didn't change
        changed = c.get_changed_docs('d17e91ae85e829a4dcc0115d5d33bf0dca179247',
                                     [u'test-user-a/my-favorite-trees.json'])
        self.assertEqual(set(), changed)
        # check a bogus doc id should work, but find nothing
        changed = c.get_changed_docs('d17e91ae85e829a4dcc0115d5d33bf0dca179247',
                                     [u'bogus/fake-trees.json'])
        self.assertEqual(set(), changed)
        # passing a foreign (or nonsense) SHA should raise a ValueError
        self.assertRaises(ValueError, c.get_changed_docs, 'bogus')


if __name__ == "__main__":
    unittest.main(verbosity=5)
