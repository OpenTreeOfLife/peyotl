#! /usr/bin/env python
from peyotl.api import NexsonStore
from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest
import copy

_LOG = get_logger(__name__)

class TestDictDiff(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.nexson_store = NexsonStore(d)

    def testStudyList(self):
        sl = self.nexson_store.study_list()
        self.assertTrue(len(sl) > 100)
if __name__ == "__main__":
    unittest.main()
