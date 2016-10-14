#! /usr/bin/env python
import unittest

from peyotl.api import TreeCollectionsAPI
from peyotl.test.support import test_collections_api
from peyotl.test.support.pathmap import get_test_repos
from peyotl.utility import get_logger

_LOG = get_logger(__name__)

test_repos = get_test_repos(['mini_collections'])


@unittest.skipIf(not test_repos,
                 'See the documentation about the maintainers test to configure your '
                 'machine to run tests that require the mini_collections repos')
class TestTreeCollectionsAPI(unittest.TestCase):
    def setUp(self):
        self.tca = TreeCollectionsAPI(None, get_from='local', locals_repos_dict=test_repos)

    def testCollectionList(self):
        cl = self.tca.collection_list
        # We assume there's always at least one collection.
        self.assertTrue(len(cl) > 0)

    def testLocalSugar(self):
        test_collections_api(self, self.tca)


if __name__ == "__main__":
    unittest.main()
