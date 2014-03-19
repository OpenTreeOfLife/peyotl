#! /usr/bin/env python
from peyotl.phylesystem.git_workflows import acquire_lock_raise, \
                                             commit_and_try_merge2master, \
                                             delete_study, \
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
        # add a second commit that should merge to master
        c += 1
        curr_obj['nexml']["^count"] = c
        v1b = commit_and_try_merge2master(ga, curr_obj, _MINI_PHYL_STUDY_ID, _TEST_AUTH_INFO, sha)
        self.assertFalse(v1b['pull_needed'])
        
        # add a third commit that should NOT merge to master
        c += 1
        curr_obj['nexml']["^count"] = c
        v2b = commit_and_try_merge2master(ga, curr_obj, _MINI_PHYL_STUDY_ID, _TEST_AUTH_INFO, sha)
        
        self.assertNotEqual(v1b['branch_name'], v2b['branch_name'])
        self.assertNotEqual(v1b['sha'], v2b['sha'])
        self.assertEqual(v1b['sha'], ga.get_master_sha()) # not locked!
        self.assertTrue(v2b['pull_needed'])
        
        # add a fourth commit onto commit 2. This should merge to master
        c += 1
        curr_obj['nexml']["^count"] = c
        v3b = commit_and_try_merge2master(ga, curr_obj, _MINI_PHYL_STUDY_ID, _TEST_AUTH_INFO, v1b['sha'])
        self.assertFalse(v3b['pull_needed'])
        
        # add a fifth commit onto commit 3. This should still NOT merge to master
        c += 1
        curr_obj['nexml']["^count"] = c
        v4b = commit_and_try_merge2master(ga, curr_obj, _MINI_PHYL_STUDY_ID, _TEST_AUTH_INFO, v2b['sha'])
        
        self.assertNotEqual(v3b['branch_name'], v4b['branch_name'])
        self.assertEqual(v2b['branch_name'], v4b['branch_name'])
        self.assertNotEqual(v3b['sha'], v4b['sha'])
        self.assertEqual(v3b['sha'], ga.get_master_sha()) # not locked!
        self.assertTrue(v4b['pull_needed'])
        
if __name__ == "__main__":
    unittest.main()
    