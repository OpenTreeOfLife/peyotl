#! /usr/bin/env python
from peyotl.api import Phylografter
from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest
import copy

_LOG = get_logger(__name__)

class TestPhylografterAPI(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.phylografter = Phylografter(d)

    def testFetchStudy(self):
        x = self.phylografter.fetch_study('252')
        sid = find_val_literal_meta_first(x['nexml'], 'ot:studyId', detect_nexson_version(x))
        self.assertTrue(sid in ['252', 'pg_252'])

    def testGetModifiedList(self):
        ml = self.phylografter.get_modified_list(list_only=True)
        self.assertTrue(len(ml) > 1000)
        from datetime import datetime
        ml = self.phylografter.get_modified_list(since_date=datetime.now(), list_only=False)
        self.assertTrue(len(ml['studies']) < 10)

if __name__ == "__main__":
    unittest.main()
