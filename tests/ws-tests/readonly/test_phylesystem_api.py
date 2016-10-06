#! /usr/bin/env python
from peyotl.api import PhylesystemAPI
from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.test.support import test_phylesystem_api_for_study
from peyotl.utility import get_logger
import unittest
import requests
import os
_LOG = get_logger(__name__)
from peyotl.phylesystem.helper import get_repos
try:
    get_repos()
    HAS_LOCAL_PHYLESYSTEM_REPOS = True
except:
    HAS_LOCAL_PHYLESYSTEM_REPOS = False


@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use '
                 'Open Tree of Life web services are disabled.')
class TestPhylesystemAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()

    def testRemoteTransSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='api', transform='server')
        test_phylesystem_api_for_study(self, pa)
    def testRemoteStudyList(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        sl = pa.study_list
        # dev/production repos should have hundreds of studies
        self.assertTrue(len(sl) > 100)
    def testPushFailureState(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        sl = pa.push_failure_state
        self.assertTrue(sl[0] is True)
    def testRemoteSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        test_phylesystem_api_for_study(self, pa)
    def testExternalSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='external')
        test_phylesystem_api_for_study(self, pa)
    def testConfig(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        x = pa.phylesystem_config
        self.assertTrue(('repo_nexml2json' in x.keys()) or ('assumed_doc_version' in x.keys()))
        # TODO: remove 'assumed_doc_version' once the preset API domain has newer code
    def testExternalURL(self):
        # N.B. that the URL for this API call is an odd one, e.g.
        #    http://devapi.opentreeoflife.org/phylesystem/external_url/pg_10
        pa = PhylesystemAPI(self.domains, get_from='api')
        u = pa.get_external_url('pg_10')
        re = requests.get(u).json()
        sid = find_val_literal_meta_first(re['nexml'], 'ot:studyId', detect_nexson_version(re))
        self.assertTrue(sid in ['10', 'pg_10'])

if __name__ == "__main__":
    unittest.main()

