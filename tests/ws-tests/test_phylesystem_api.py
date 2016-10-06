#! /usr/bin/env python
from peyotl.api import PhylesystemAPI
from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.test.support import test_phylesystem_api_pg10
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
        test_phylesystem_api_pg10(self, pa)
    @unittest.skipIf(not HAS_LOCAL_PHYLESYSTEM_REPOS,
                     'only available if you are have a [phylesystem] section '
                     'with "parent" variable in your peyotl config')
    def testLocalStudyList(self):
        pa = PhylesystemAPI(self.domains, get_from='local')
        sl = pa.study_list
        # local repo should have just a few studies
        #@TODO we need a better test, I changed it from 10 to 10000. 
        # because I use my own fork of a large phylesystem in my tests
        # I'm not sure what invariants we should check for, but 
        # length of study list is probably not one.
        self.assertTrue(len(sl) < 10000)
    def testRemoteStudyList(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        sl = pa.study_list
        # dev/production repos should have hundreds of studies
        self.assertTrue(len(sl) > 100)
    def testPushFailureState(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        sl = pa.push_failure_state
        self.assertTrue(sl[0] is True)
    def testFetchStudyRemote(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        x = pa.get_study('pg_10')['data']
        sid = find_val_literal_meta_first(x['nexml'], 'ot:studyId', detect_nexson_version(x))
        self.assertTrue(sid in ['10', 'pg_10'])
    def testRemoteSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        test_phylesystem_api_pg10(self, pa)
    def testExternalSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='external')
        test_phylesystem_api_pg10(self, pa)
    @unittest.skipIf(not HAS_LOCAL_PHYLESYSTEM_REPOS,
                     'only available if you are have a [phylesystem]'
                     ' section with "parent" variable in your peyotl config')
    def testLocalSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='local')
        test_phylesystem_api_pg10(self, pa)
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

