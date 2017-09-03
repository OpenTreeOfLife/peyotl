#! /usr/bin/env python
import unittest

from peyotl.api import IllustrationsAPI
from peyotl.test.support import test_illustrations_api
from peyotl.test.support.pathmap import get_test_repos
from peyotl.utility import get_logger

_LOG = get_logger(__name__)

test_repos = get_test_repos(['mini_illustrations'])


@unittest.skipIf(not test_repos,
                 'See the documentation about the maintainers test to configure your '
                 'machine to run tests that require the mini_illustrations repo')
class TestTreeIllustrationsAPI(unittest.TestCase):
    def setUp(self):
        self.tia = IllustrationsAPI(None, get_from='local', locals_repos_dict=test_repos)

    def testIllustrationList(self):
        il = self.tia.illustration_list
        # We assume there's always at least one illustration.
        self.assertTrue(len(il) > 0)

    def testLocalSugar(self):
        test_illustrations_api(self, self.tia)


if __name__ == "__main__":
    unittest.main()
