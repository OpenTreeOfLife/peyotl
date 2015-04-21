#! /usr/bin/env python
from peyotl.api import TreeCollectionsAPI
#from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest
import requests
from pprint import pprint

_LOG = get_logger(__name__)
from peyotl.collections.helper import get_repos
try:
    get_repos()
    HAS_LOCAL_COLLECTIONS_REPOS = True
except:
    HAS_LOCAL_COLLECTIONS_REPOS = False


class TestTreeCollectionsAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()
    def _do_sugar_tests(self, tca):
        try:
            c = tca.get('TestUserB/my-favorite-trees')
        except:
            # alternate collection for remote/proxied docstore
            c = tca.get('jimallman/my-test-collection')
        cn = c['name']
        self.assertTrue(cn in [u'My favorite trees!', u'My test collection'])
    @unittest.skipIf(not HAS_LOCAL_COLLECTIONS_REPOS,
                     'only available if you are have a [phylesystem] section ' \
                     'with "parent" variable in your peyotl config')
    def testCollectionList(self):
        tca = TreeCollectionsAPI(self.domains, get_from='local')
        cl = tca.collection_list
        # We assume there's always at least one collection.
        self.assertTrue(len(cl) > 0)
    def testPushFailureState(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        #import pdb; pdb.set_trace()
        sl = tca.push_failure_state
        self.assertTrue(sl[0] is True)
    def testFetchCollectionRemote(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        c = tca.get_collection('jimallman/my-test-collection')
        # N.B. we get the JSON "wrapper" with history, etc.
        cn = c['data']['name']
        self.assertTrue(cn == u'My test collection')
    def testRemoteSugar(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        self._do_sugar_tests(tca)
    def testExternalSugar(self):
        tca = TreeCollectionsAPI(self.domains, get_from='external')
        self._do_sugar_tests(tca)
    @unittest.skipIf(not HAS_LOCAL_COLLECTIONS_REPOS,
                     'only available if you are have a [phylesystem]' \
                     ' section with "parent" variable in your peyotl config')
    def testLocalSugar(self):
        tca = TreeCollectionsAPI(self.domains, get_from='local')
        self._do_sugar_tests(tca)
    def testConfig(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        x = tca.store_config
        self.assertTrue('assumed_doc_version' in x.keys())
    @unittest.skip('See https://github.com/OpenTreeOfLife/phylesystem-api/issues/116 ')
    def testExternalURL(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        u = tca.get_external_url('TestUserB/my-favorite-trees')
        re = requests.get(u).json()
        self.assertTrue(c['name'] == u'My test collection')

if __name__ == "__main__":
    unittest.main()

