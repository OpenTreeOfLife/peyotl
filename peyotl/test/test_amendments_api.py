#! /usr/bin/env python
import os
from peyotl.api import TaxonomicAmendmentsAPI
#from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
from peyotl.amendments import get_empty_amendment
from peyotl.utility.str_util import slugify, \
                                    increment_slug
from requests.exceptions import HTTPError
import unittest
from pprint import pprint

_LOG = get_logger(__name__)
from peyotl.amendments.helper import get_repos
try:
    get_repos()
    HAS_LOCAL_AMENDMENTS_REPOS = True
except:
    HAS_LOCAL_AMENDMENTS_REPOS = False

def raise_HTTPError_with_more_detail(err):
    # show more useful information (JSON payload) from the server
    details = err.response.text
    raise ValueError("{e}, details: {m}".format(e=err, m=details))

@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use ' \
                 'Open Tree of Life web services are disabled.')
class TestTaxonomicAmendmentsAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()
    def tearDown(self):
        # TODO: restore all docstore repos to their prior state?
        #   - 'git revert' to force remote master "backwards"?
        #   - delete new amendments in each test? (will add to history)
        #   - suspend git push to remote, and undo history?
        pass
    def _do_sugar_tests(self, taa):
        try:
            a = taa.get('additions-5000000-5000003')
            cn = a['study_id']
            self.assertTrue(cn in [u'ot_234',])
        except:
            # try alternate amendments (and study_id) for remote/proxied docstores
            try:
                # this is an amendment in the production repo!
                a = taa.get('additions-5861452-5861452')
                cn = a['study_id']
                self.assertTrue(cn in [u'ot_520',])
            except:
                # this is an amendment in the devapi repo (amendments-0)!
                a = taa.get('additions-10000000-10000001')
                cn = a['study_id']
                self.assertTrue(cn in [u'pg_2606',])
    @unittest.skipIf(not HAS_LOCAL_AMENDMENTS_REPOS,
                     'only available if you are have a [phylesystem] section ' \
                     'with "parent" variable in your peyotl config')
    def testAmendmentList(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='local')
        al = taa.amendment_list
        # We assume there's always at least one amendment.
        self.assertTrue(len(al) > 0)
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
    #@unittest.skipIf(not os.environ.get('GITHUB_OAUTH_TOKEN'),
    #                 'only available if GITHUB_OAUTH_TOKEN is found in env ' \
    #                 ' (required to use docstore write methods)')
    #def testCRUD1_CreateAmendmentRemote(self):
    #    # drive RESTful API via wrapper
    #    taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
    #    # remove any prior clones of our tests amendment? or let them pile up for now?
    #    al = taa.amendment_list
    #    test_amendment_study_id = 'ot_999999'
    #    # TODO: fetch next ottid to mint, to determine the resulting amendment id?
    #    expected_id = "additions-9999999-9999999"
    #    # generate a new amendment and set some properties
    #    ajson = get_empty_amendment()
    #    ajson['study_id'] = test_amendment_study_id
    #    commit_msg = 'Test of creating amendments via API wrapper'
    #    #import pdb; pdb.set_trace()
    #    result = taa.post_amendment(ajson,
    #                                commit_msg)
    #    al = taa.amendment_list
    #    self.assertEqual(result['error'], 0)
    #    self.assertEqual(result['merge_needed'], False)
    #    self.assertEqual(result['resource_id'], expected_id)
    #    self.assertTrue(expected_id in al)
    #@unittest.skipIf(not os.environ.get('GITHUB_OAUTH_TOKEN'),
    #                 'only available if GITHUB_OAUTH_TOKEN is found in env ' \
    #                 ' (required to use docstore write methods)')
    #def testCRUD2_ModifyAmendmentRemote(self):
    #    # drive RESTful API via wrapper
    #    taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
    #    aid = 'additions-0000000-0000000'
    #    try:
    #        a = taa.get_amendment(aid)
    #    except HTTPError as err:
    #        raise_HTTPError_with_more_detail(err)
    #    except Exception as err:
    #        raise err
    #    # N.B. we get the JSON "wrapper" with history, etc.
    #    ac = a['data']['comment']
    #    # let's treat this as a numeric value and increment it
    #    try:
    #        ac_number = int(ac)
    #    except:
    #        ac_number = 0
    #    ac_number += 1
    #    a['data']['comment'] = str(ac_number)
    #    a = taa.put_amendment(aid,
    #                          a['data'],
    #                          a['sha'])  # TODO: add commit msg?
    #    # retrieve the new version and see if it has the modified comment
    #    try:
    #        a = taa.get_amendment(aid)
    #    except HTTPError as err:
    #        raise_HTTPError_with_more_detail(err)
    #    except Exception as err:
    #        raise err
    #    self.assertEqual(a['data']['comment'], str(ac_number))
    #@unittest.skipIf(not os.environ.get('GITHUB_OAUTH_TOKEN'),
    #                 'only available if GITHUB_OAUTH_TOKEN is found in env ' \
    #                 ' (required to use docstore write methods)')
    #def testCRUD3_DeleteAmendmentRemote(self):
    #    # drive RESTful API via wrapper
    #    taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
    #    # ASSUME that our amendment was created in CRUD1 test above
    #    aid = 'additions-6666666-6666666'
    #    al = taa.amendment_list
    #    self.assertTrue(aid in al)
    #    # now try to clobber it
    #    try:
    #        a = taa.get_amendment(aid)
    #    except HTTPError as err:
    #        raise_HTTPError_with_more_detail(err)
    #    except Exception as err:
    #        raise err
    #    a = taa.delete_amendment(aid,
    #                             a['sha'])
    #    # is it really gone?
    #    al = taa.amendment_list
    #    self.assertTrue(aid not in al)

    def testRemoteSugar(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
        try:
            self._do_sugar_tests(taa)
        except HTTPError as err:
            raise_HTTPError_with_more_detail(err)
        except Exception as err:
            raise err
    def testExternalSugar(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='external')
        self._do_sugar_tests(taa)
    @unittest.skipIf(not HAS_LOCAL_AMENDMENTS_REPOS,
                     'only available if you are have a [phylesystem]' \
                     ' section with "parent" variable in your peyotl config')
    def testLocalSugar(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='local')
        self._do_sugar_tests(taa)
    def testConfig(self):
        taa = TaxonomicAmendmentsAPI(self.domains, get_from='api')
        x = taa.store_config
        self.assertTrue('assumed_doc_version' in x.keys())
    #TODO: add testExternalURL and support for this call in amendments API?

if __name__ == "__main__":
    unittest.main()

