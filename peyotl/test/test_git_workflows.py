#! /usr/bin/env python
from peyotl.phylesystem.git_workflows import acquire_lock_raise, \
                                             commit_and_try_merge2master, \
                                             delete_and_push, \
                                             GitWorkflowError, \
                                             validate_and_convert_nexson
from peyotl.phylesystem import Phylesystem
import unittest
import codecs
import json
from peyotl.nexson_syntax import read_as_json
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

phylesystem = Phylesystem(pathmap.get_test_repos())

_MINI_PHYL_SHA1 = 'aa8964b55bfa930a91af7a436f55f0acdc94b918'
_MINI_PHYL_STUDY_ID = '9'
_TEST_AUTH_INFO = {
    'name': 'test_name',
    'email': 'test_email@example.org',
    'login': 'test_gh_login',
}

class TestPhylesystem(unittest.TestCase):
    def xtestSimple(self):
        ga = phylesystem.create_git_action(_MINI_PHYL_STUDY_ID)
        ga.acquire_lock()
        try:
            curr, sha = ga.return_study(_MINI_PHYL_STUDY_ID)
        finally:
            ga.release_lock()
        curr_obj = json.loads(curr)
        c = curr_obj['nexml'].get("^count", 0)
        c += 1
        curr_obj['nexml']["^count"] = c
        commit_and_try_merge2master(ga, curr_obj, _MINI_PHYL_STUDY_ID, _TEST_AUTH_INFO, sha)
    def testBranched(self):
        ga = phylesystem.create_git_action(_MINI_PHYL_STUDY_ID)
        ga.acquire_lock()
        try:
            curr, sha = ga.return_study(_MINI_PHYL_STUDY_ID)
        finally:
            ga.release_lock()
        _LOG.debug('test sha = "{}"'.format(sha))
        curr_obj = json.loads(curr)
        c = curr_obj['nexml'].get("^count", 0)
        c += 1
        curr_obj['nexml']["^count"] = c
        v1b = commit_and_try_merge2master(ga, curr_obj, _MINI_PHYL_STUDY_ID, _TEST_AUTH_INFO, sha)
        c += 1
        curr_obj['nexml']["^count"] = c
        v2b = commit_and_try_merge2master(ga, curr_obj, _MINI_PHYL_STUDY_ID, _TEST_AUTH_INFO, sha)
        self.assertNotEqual(v1b['branch_name'], v2b['branch_name'])
        self.assertNotEqual(v1b['sha'], v2b['sha'])
        self.assertEqual(v1b['sha'], ga.get_master_sha()) # not locked!
        
if __name__ == "__main__":
    unittest.main()
    