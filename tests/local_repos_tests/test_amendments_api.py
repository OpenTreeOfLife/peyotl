#! /usr/bin/env python
import unittest

from peyotl.api import TaxonomicAmendmentsAPI
from peyotl.test.support import test_amendments_api
from peyotl.test.support.pathmap import get_test_repos
from peyotl.utility import get_logger

_LOG = get_logger(__name__)

test_repos = get_test_repos(['mini_amendments'])


@unittest.skipIf(not test_repos,
                 'See the documentation about the maintainers test to configure your '
                 'machine to run tests that require the mini_amendments repos')
class TestTaxonomicAmendmentsAPI(unittest.TestCase):
    def setUp(self):
        self.taa = TaxonomicAmendmentsAPI(None, get_from='local', locals_repos_dict=test_repos)

    def testAmendmentList(self):
        al = self.taa.amendment_list
        # We assume there's always at least one amendment.
        self.assertTrue(len(al) > 0)

    def testLocalSugar(self):
        test_amendments_api(self, self.taa)


if __name__ == "__main__":
    unittest.main()
