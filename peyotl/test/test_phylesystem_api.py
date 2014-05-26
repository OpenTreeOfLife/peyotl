#! /usr/bin/env python
from peyotl.api import NexsonStore
from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest
import requests
import copy

_LOG = get_logger(__name__)

class TestDictDiff(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.nexson_store = NexsonStore(d)
    def testStudyList(self):
        sl = self.nexson_store.study_list()
        self.assertTrue(len(sl) > 100)
    def testFetchStudy(self):
        x = self.nexson_store.get_study('pg_10')['data']
        sid = find_val_literal_meta_first(x['nexml'], 'ot:studyId', detect_nexson_version(x))
        self.assertTrue(sid in ['10', 'pg_10'])
    def testConfig(self):
        x = self.nexson_store.phylesystem_config()
        self.assertTrue('repo_nexml2json' in x.keys())
    def testExternalURL(self):
        x = self.nexson_store.external_url('pg_10')
        u = x['url']
        r = requests.get(u).json()
        sid = find_val_literal_meta_first(r['nexml'], 'ot:studyId', detect_nexson_version(r))
        self.assertTrue(sid in ['10', 'pg_10'])

if __name__ == "__main__":
    unittest.main()
