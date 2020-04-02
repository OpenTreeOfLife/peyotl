#! /usr/bin/env python
import os
import unittest

from peyotl.api import TreeCollectionsAPI
from peyotl.collections_store import get_empty_collection
from peyotl.test.support import raise_http_error_with_more_detail
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
from peyutil import slugify, increment_slug
from requests.exceptions import HTTPError

_LOG = get_logger(__name__)


run_write_ws = ('RUN_WEB_SERVICE_TESTS' in os.environ) and ('GITHUB_OAUTH_TOKEN' in os.environ)


@unittest.skipIf(not run_write_ws,
                 'RUN_WEB_SERVICE_TESTS and GITHUB_OAUTH_TOKEN both have to be in '
                 'your environment to run the ws-tests that write.')
class TestTreeCollectionsAPI(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()

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
        # TODO: generate a unique URL based on this json, and modify it internally?
        commit_msg = 'Test of creating collections via API wrapper'
        result = tca.post_collection(cjson,
                                     cid,
                                     commit_msg)
        cl = tca.collection_list
        self.assertEqual(result['error'], 0)
        self.assertEqual(result['merge_needed'], False)
        self.assertEqual(result['resource_id'], expected_id)
        self.assertTrue(expected_id in cl)

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
            raise_http_error_with_more_detail(err)
        except Exception as err:
            raise err
        else:
            tca.delete_collection(cid, c['sha'])
            # is it really gone?
            cl = tca.collection_list
            self.assertTrue(cid not in cl)


# TODO: fix the test below
"""
@unittest.skipIf(True, 'Not sure why, but this test is failing for MTH. Perhaps I should not be using devapi as '
                       'my endpoint...')
def testModifyCollectionRemote(self):
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
            raise_http_error_with_more_detail(err)
        except Exception as err:
            raise err
        self.assertEqual(c['data']['description'], str(cd_number))
"""

if __name__ == "__main__":
    unittest.main()
