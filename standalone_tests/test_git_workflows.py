#! /usr/bin/env python
from peyotl.phylesystem.git_workflows import acquire_lock_raise, \
                                             commit_and_try_merge2master, \
                                             delete_study, \
                                             GitWorkflowError, \
                                             merge_from_master
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
import unittest
import codecs
import json
import copy
from peyotl.nexson_syntax import read_as_json
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

phylesystem = Phylesystem(pathmap.get_test_repos())

_MINI_PHYL_SHA1 = 'aa8964b55bfa930a91af7a436f55f0acdc94b918'
_SID = '9'
_AUTH = {
    'name': 'test_name',
    'email': 'test_email@example.org',
    'login': 'test_gh_login',
}

class TestPhylesystem(unittest.TestCase):
    def xtestSimple(self):
        ga = phylesystem.create_git_action(_SID)
        ga.acquire_lock()
        try:
            curr, sha, wip_map = ga.return_study(_SID, return_WIP_map=True)
        finally:
            ga.release_lock()
        curr_obj = json.loads(curr)
        ac = curr_obj['nexml'].get("^acount", 0)
        ac += 1
        curr_obj['nexml']["^acount"] = ac
        commit_and_try_merge2master(ga, curr_obj, _SID, _AUTH, sha)

    def testBranched(self):
        ga = phylesystem.create_git_action(_SID)
        ga.acquire_lock()
        try:
            curr, sha, wip_map = ga.return_study(_SID, return_WIP_map=True)
        finally:
            ga.release_lock()
        _LOG.debug('test sha = "{}"'.format(sha))
        self.assertEquals(wip_map.keys(), ['master'])
        acurr_obj = json.loads(curr)
        zcurr_obj = copy.deepcopy(acurr_obj)
        ac = acurr_obj['nexml'].get("^acount", 0)
        # add a second commit that should merge to master
        ac += 1
        acurr_obj['nexml']["^acount"] = ac
        v1b = commit_and_try_merge2master(ga, acurr_obj, _SID, _AUTH, sha)
        self.assertFalse(v1b['merge_needed'])
        
        # add a third commit that should NOT merge to master
        zc = zcurr_obj['nexml'].get("^zcount", 0)
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        v2b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, sha)
        
        self.assertNotEqual(v1b['branch_name'], v2b['branch_name'])
        self.assertNotEqual(v1b['sha'], v2b['sha'])
        self.assertEqual(v1b['sha'], ga.get_master_sha()) # not locked!
        self.assertTrue(v2b['merge_needed'])

        # fetching studies (GETs in the API) should report 
        # the existence of multiple branches for this study...
        ga.acquire_lock()
        try:
            t, ts, wip_map = ga.return_study(_SID, return_WIP_map=True)
        finally:
            ga.release_lock()
        self.assertEquals(wip_map['master'], v1b['sha'])
        self.assertEquals(wip_map['test_gh_login_study_9_0'], v2b['sha'])
        
        # but not for other studies...
        ga.acquire_lock()
        try:
            t, ts, wip_map = ga.return_study('10', return_WIP_map=True)
        finally:
            ga.release_lock()
        self.assertEquals(wip_map['master'], v1b['sha'])
        self.assertEquals(wip_map.keys(), ['master'])
        
        # add a fourth commit onto commit 2. This should merge to master
        ac += 1
        acurr_obj['nexml']["^acount"] = ac
        v3b = commit_and_try_merge2master(ga, acurr_obj, _SID, _AUTH, v1b['sha'])
        self.assertFalse(v3b['merge_needed'])
        
        # add a fifth commit onto commit 3. This should still NOT merge to master
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        v4b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, v2b['sha'])
        
        self.assertNotEqual(v3b['branch_name'], v4b['branch_name'])
        self.assertEqual(v2b['branch_name'], v4b['branch_name'])
        self.assertNotEqual(v3b['sha'], v4b['sha'])
        self.assertEqual(v3b['sha'], ga.get_master_sha()) # not locked!
        self.assertTrue(v4b['merge_needed'])
        
        # sixth commit is the merge
        mblob = merge_from_master(ga, _SID, _AUTH, v4b['sha'])
        self.assertEqual(mblob["error"], 0)
        self.assertEqual(mblob["resource_id"], _SID)
        
        
        # add a 7th commit onto commit 6. This should NOT merge to master because we don't give it the secret arg.
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        v5b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, mblob['sha'])
        self.assertNotEqual(v3b['sha'], v5b['sha'])
        self.assertTrue(v5b['merge_needed'])
        
        # add a 7th commit onto commit 6. This should merge to master because we don't give it the secret arg.
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        v6b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, v5b['sha'], merged_sha=mblob['merged_sha'])
        self.assertNotEqual(v3b['sha'], v6b['sha'])
        self.assertEqual(v6b['sha'], ga.get_master_sha()) # not locked!
        self.assertFalse(v6b['merge_needed'])
        self.assertEqual(v6b['branch_name'], 'master')
        
        # after the merge we should be back down to 1 branch for this study
        ga.acquire_lock()
        try:
            t, ts, wip_map = ga.return_study(_SID, return_WIP_map=True)
        finally:
            ga.release_lock()
        self.assertEquals(wip_map.keys(), ['master'])
        
if __name__ == "__main__":
    unittest.main()
    