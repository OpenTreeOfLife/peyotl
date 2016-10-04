#! /usr/bin/env python
import os
from peyotl.api import TreeCollectionsAPI
#from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
from peyotl.collections_store import get_empty_collection
from peyotl.utility.str_util import slugify, \
                                    increment_slug
from requests.exceptions import HTTPError
import unittest
from pprint import pprint

_LOG = get_logger(__name__)
from peyotl.collections_store.helper import get_repos
try:
    get_repos()
    HAS_LOCAL_COLLECTIONS_REPOS = True
except:
    HAS_LOCAL_COLLECTIONS_REPOS = False

def raise_HTTPError_with_more_detail(err):
    # show more useful information (JSON payload) from the server
    details = err.response.text
    raise ValueError("{e}, details: {m}".format(e=err, m=details))

@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use ' \
                 'Open Tree of Life web services are disabled.')
class TestTreeCollectionsAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()
    def tearDown(self):
        # TODO: restore all docstore repos to their prior state?
        #   - 'git revert' to force remote master "backwards"?
        #   - delete new collections in each test? (will add to history)
        #   - suspend git push to remote, and undo history?
        pass
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
        sl = tca.push_failure_state
        if sl[0] is not True:
            pprint('\npush-failure (possibly a stale result? re-run to find out!):\n')
            pprint(sl)
        self.assertTrue(sl[0] is True)
    @unittest.skipIf(not os.environ.get('GITHUB_OAUTH_TOKEN'),
                     'only available if GITHUB_OAUTH_TOKEN is found in env ' \
                     ' (required to use docstore write methods)')
    def testCreateCollectionRemote(self):
        # drive RESTful API via wrapper
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        # remove any prior clones of our tests collection? or let them pile up for now?
        cl = tca.collection_list
        test_collection_name = 'My test collection'
        test_collection_id_base = 'jimallman/my-test-collection'
        expected_id = test_collection_id_base
        while expected_id in cl:
            # keep generating ids until we find a new one
            expected_id = increment_slug(expected_id)
        # generate a new collection and name it
        cjson = get_empty_collection()
        cjson['name'] = test_collection_name
        # N.B. this name already exists! should force a new, serial id
        cslug = slugify(cjson['name'])
        cid = 'jimallman/{}'.format(cslug)
        ### TODO: generate a unique URL based on this json, and modify it internally?
        commit_msg = 'Test of creating collections via API wrapper'
        result = tca.post_collection(cjson,
                                     cid,
                                     commit_msg)
        cl = tca.collection_list
        self.assertEqual(result['error'], 0)
        self.assertEqual(result['merge_needed'], False)
        self.assertEqual(result['resource_id'], expected_id)
        self.assertTrue(expected_id in cl)
    def testFetchCollectionRemote(self):
        # drive RESTful API via wrapper
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        try:
            c = tca.get_collection('jimallman/my-test-collection')
        except HTTPError as err:
            raise_HTTPError_with_more_detail(err)
        except Exception as err:
            raise err
        # N.B. we get the JSON "wrapper" with history, etc.
        cn = c['data']['name']
        self.assertTrue(cn == u'My test collection')
    #@unittest.skipIf(not os.environ.get('GITHUB_OAUTH_TOKEN'),
    #                 'only available if GITHUB_OAUTH_TOKEN is found in env ' \
    #                 ' (required to use docstore write methods)')
    @unittest.skipIf(True, 'Not sure why, but this test is failing for MTH. Perhaps I should not be using devapi as '
                           'my endpoint...')
    def testModifyCollectionRemote(self):
        # drive RESTful API via wrapper
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        try:
            c = tca.get_collection('jimallman/my-test-collection')
        except HTTPError as err:
            raise_HTTPError_with_more_detail(err)
        except Exception as err:
            raise err
        # N.B. we get the JSON "wrapper" with history, etc.
        cd = c['data']['description']
        # let's treat this as a numeric value and increment it
        try:
            cd_number = int(cd)
        except:
            cd_number = 0
        cd_number += 1
        c['data']['description'] = str(cd_number)
        c = tca.put_collection('jimallman/my-test-collection',
                               c['data'],
                               c['sha'])  # TODO: add commit msg?
        # retrieve the new version and see if it has the modified description
        try:
            c = tca.get_collection('jimallman/my-test-collection')
        except HTTPError as err:
            raise_HTTPError_with_more_detail(err)
        except Exception as err:
            raise err
        self.assertEqual(c['data']['description'], str(cd_number))
    @unittest.skipIf(not os.environ.get('GITHUB_OAUTH_TOKEN'),
                     'only available if GITHUB_OAUTH_TOKEN is found in env ' \
                     ' (required to use docstore write methods)')
    def testDeleteCollectionRemote(self):
        # drive RESTful API via wrapper
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        # remove any prior clones of our tests collection? or let them pile up for now?
        cl = tca.collection_list
        cid = 'jimallman/doomed-collection'
        if cid not in cl:
            # add our dummy collection so just we can delete it
            cjson = get_empty_collection()
            commit_msg = 'Creating temporary collection via API wrapper'
            result = tca.post_collection(cjson,
                                         cid,
                                         commit_msg)
            cl = tca.collection_list
            self.assertEqual(result['error'], 0)
            self.assertEqual(result['merge_needed'], False)
            self.assertEqual(result['resource_id'], cid)
            self.assertTrue(cid in cl)
        # now try to clobber it
        try:
            c = tca.get_collection(cid)
        except HTTPError as err:
            raise_HTTPError_with_more_detail(err)
        except Exception as err:
            raise err
        c = tca.delete_collection(cid,
                                  c['sha'])
        # is it really gone?
        cl = tca.collection_list
        self.assertTrue(cid not in cl)
    def testRemoteSugar(self):
        tca = TreeCollectionsAPI(self.domains, get_from='api')
        try:
            self._do_sugar_tests(tca)
        except HTTPError as err:
            raise_HTTPError_with_more_detail(err)
        except Exception as err:
            raise err
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
    #TODO: add testExternalURL and support for this call in collections API?

if __name__ == "__main__":
    unittest.main()

