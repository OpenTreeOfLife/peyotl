#! /usr/bin/env python
import os
import unittest
from pprint import pprint

from peyotl.api import TreeCollectionsAPI
from peyotl.test.support import test_collections_api, raise_http_error_with_more_detail
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
from requests.exceptions import HTTPError

_LOG = get_logger(__name__)


@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use '
                 'Open Tree of Life web services are disabled.')
class TestTreeCollectionsAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()

    def testPushFailureState(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        sl = tca.push_failure_state
        if sl[0] is not True:
            pprint('\npush-failure (possibly a stale result? re-run to find out!):\n')
            pprint(sl)
        self.assertTrue(sl[0] is True)

    def testFetchCollectionRemote(self):
        # drive RESTful API via wrapper
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        try:
            c = tca.get_collection('jimallman/my-test-collection')
        except HTTPError as err:
            raise_http_error_with_more_detail(err)
        except Exception as err:
            raise err
        else:
            # N.B. we get the JSON "wrapper" with history, etc.
            cn = c['data']['name']
            self.assertTrue(cn == u'My test collection')

    def testRemoteSugar(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        try:
            test_collections_api(self, tca)
        except HTTPError as err:
            raise_http_error_with_more_detail(err)
        except Exception as err:
            raise err

    def testExternalSugar(self):
        tca = TreeCollectionsAPI(self.domains, get_from='external')
        test_collections_api(self, tca)

    def testConfig(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        x = tca.store_config
        self.assertTrue('assumed_doc_version' in x.keys())
        # TODO: add testExternalURL and support for this call in collections API?


if __name__ == "__main__":
    unittest.main()
