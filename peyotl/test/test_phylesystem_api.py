#! /usr/bin/env python
from peyotl.api import PhylesystemAPI
from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest
import requests

_LOG = get_logger(__name__)
from peyotl.phylesystem import get_repos
try:
    r = get_repos()
    HAS_LOCAL_PHYLESYSTEM_REPOS = True
except:
    HAS_LOCAL_PHYLESYSTEM_REPOS = False


class TestPhylesystemAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()
    def _do_sugar_tests(self, pa):
        x = pa.get('pg_10')['data']
        sid = find_val_literal_meta_first(x['nexml'], 'ot:studyId', detect_nexson_version(x))
        self.assertTrue(sid in ['10', 'pg_10'])
        y = pa.get('pg_10', tree_id='tree3', format='newick')
        self.assertTrue(y.startswith('('))
    def testRemoteTransSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='api', transform='server')
        self._do_sugar_tests(pa)
    @unittest.skipIf(not HAS_LOCAL_PHYLESYSTEM_REPOS, 'only available if you are have a [phylesystem] section with "parent" variable in your peyotl config')
    def testStudyList(self):
        pa = PhylesystemAPI(self.domains, get_from='local')
        sl = pa.study_list
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
        self._do_sugar_tests(pa)
    def testExternalSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='external')
        self._do_sugar_tests(pa)
    @unittest.skipIf(not HAS_LOCAL_PHYLESYSTEM_REPOS, 'only available if you are have a [phylesystem] section with "parent" variable in your peyotl config')
    def testLocalSugar(self):
        pa = PhylesystemAPI(self.domains, get_from='local')
        self._do_sugar_tests(pa)
    def testConfig(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        x = pa.phylesystem_config
        self.assertTrue('repo_nexml2json' in x.keys())
    @unittest.skip('See https://github.com/OpenTreeOfLife/phylesystem-api/issues/116 ')
    def testExternalURL(self):
        pa = PhylesystemAPI(self.domains, get_from='api')
        u = pa.get_external_url('pg_10')
        r = requests.get(u).json()
        sid = find_val_literal_meta_first(r['nexml'], 'ot:studyId', detect_nexson_version(r))
        self.assertTrue(sid in ['10', 'pg_10'])

if __name__ == "__main__":
    unittest.main()
