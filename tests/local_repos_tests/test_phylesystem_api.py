#! /usr/bin/env python
import unittest

from peyotl.api import PhylesystemAPI
from peyotl.test.support import test_phylesystem_api_for_study
from peyotl.test.support.pathmap import get_test_repos
from peyotl.utility import get_logger

_LOG = get_logger(__name__)

test_repos = get_test_repos(['mini_phyl', 'mini_system'])


@unittest.skipIf(not test_repos,
                 'See the documentation about the maintainers test to configure your '
                 'machine to run tests that require the mini_phyl and mini_system repos')
class TestPhylesystemAPI(unittest.TestCase):
    def setUp(self):
        self.pa = PhylesystemAPI(None, get_from='local', locals_repos_dict=test_repos)

    def testLocalStudyList(self):
        sl = self.pa.study_list
        # local repo should have just a few studies
        # @TODO we need a better test, I changed it from 10 to 10000.
        # because I use my own fork of a large phylesystem in my tests
        # I'm not sure what invariants we should check for, but 
        # length of study list is probably not one.
        self.assertTrue(len(sl) < 10000)

    def testLocalSugar(self):
        test_phylesystem_api_for_study(self, self.pa, 'xy_10')


if __name__ == "__main__":
    unittest.main()
