#! /usr/bin/env python
import os
import unittest
from pprint import pprint

from peyotl.api import TaxonomicAmendmentsAPI
from peyotl.test.support import test_amendments_api, raise_http_error_with_more_detail
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
from requests.exceptions import HTTPError

_LOG = get_logger(__name__)


@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use '
                 'Open Tree of Life web services are disabled.')
class TestTaxonomicAmendmentsAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()

    def testPushFailureState(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
        sl = taa.push_failure_state
        if sl[0] is not True:
            pprint('\npush-failure (possibly a stale result? re-run to find out!):\n')
            pprint(sl)
        self.assertTrue(sl[0] is True)

    def testFetchAmendmentRemote(self):
        # drive RESTful API via wrapper
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
        try:
            # this is an amendment in the production repo!
            a = taa.get_amendment('additions-5861452-5861452')
            # N.B. we get the JSON "wrapper" with history, etc.
            sid = a['data']['study_id']
            self.assertTrue(sid == u'ot_520')
        except:
            # try alternate amendment (and study_id) in the devapi repo (amendments-0)!
            a = taa.get_amendment('additions-10000000-10000001')
            # N.B. we get the JSON "wrapper" with history, etc.
            sid = a['data']['study_id']
            self.assertTrue(sid == u'pg_2606')

    def testRemoteSugar(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
        try:
            test_amendments_api(self, taa)
        except HTTPError as err:
            raise_http_error_with_more_detail(err)
        except Exception as err:
            raise err

    def testExternalSugar(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='external')
        test_amendments_api(self, taa)

    def testLocalSugar(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='local')
        test_amendments_api(self, taa)

    def testConfig(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
        x = taa.store_config
        self.assertTrue('assumed_doc_version' in x.keys())
        # TODO: add testExternalURL and support for this call in amendments API?


if __name__ == "__main__":
    unittest.main()
