#! /usr/bin/env python
from peyotl.git_storage.git_workflow import acquire_lock_raise
from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
                                             GitWorkflowError
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.utility.input_output import read_as_json
import unittest
import codecs
import json
import copy
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

phylesystem = Phylesystem(pathmap.get_test_repos())

_MINI_PHYL_SHA1 = '2d59ab892ddb3d09d4b18c91470b8c1c4cca86dc'
_SID = 'xy_10'
_AUTH = {
    'name': 'test_name',
    'email': 'test_email@example.org',
    'login': 'test_gh_login',
}

class TestPhylesystemDel(unittest.TestCase):
    def testDelStudy(self):
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
        # add a commit that should merge to master
        acount_at_sha = ac
        ac += 1
        acurr_obj['nexml']["^acount"] = ac
        v1b = commit_and_try_merge2master(ga, acurr_obj, _SID, _AUTH, sha)
        v1bsha = v1b['sha']
        acount_at_v1bsha = ac
        self.assertFalse(v1b['merge_needed'])
        sidl = phylesystem.get_study_ids()
        self.assertIn(_SID, sidl)
        v2b = phylesystem.delete_study(_SID, _AUTH, sha)
        v2bsha = v2b['sha']
        self.assertTrue(v2b['merge_needed'])
        sidl = phylesystem.get_study_ids()
        self.assertIn(_SID, sidl)
        curr, naked_get_sha, wip_map = phylesystem.return_study(_SID, return_WIP_map=True)
        self.assertEquals(naked_get_sha, v1bsha)
        v3b = phylesystem.delete_study(_SID, _AUTH, naked_get_sha)
        v3bsha = v3b['sha']
        self.assertFalse(v3b['merge_needed'])
        sidl = phylesystem.get_study_ids()
        self.assertNotIn(_SID, sidl)
        self.assertRaises(KeyError, phylesystem.return_study, _SID, return_WIP_map=True)
        self.assertRaises(KeyError, phylesystem.return_study, _SID, commit_sha=v2bsha, return_WIP_map=True)
        self.assertRaises(KeyError, phylesystem.return_study, _SID, commit_sha=v3bsha, return_WIP_map=True)
        curr, naked_get_sha, wip_map = phylesystem.return_study(_SID, commit_sha=sha, return_WIP_map=True)
        self.assertEquals(acount_at_sha, curr['nexml'].get("^acount", 0))
        curr, naked_get_sha, wip_map = phylesystem.return_study(_SID, commit_sha=v1bsha, return_WIP_map=True)
        self.assertEquals(acount_at_v1bsha, curr['nexml']["^acount"])
        ga = phylesystem.create_git_action(_SID) # assert no raise
        sidl = phylesystem.get_study_ids()
        self.assertNotIn(_SID, sidl)
        ac += 1
        curr['nexml']["^acount"] = ac
        ga = phylesystem.create_git_action(_SID)
        v4b = commit_and_try_merge2master(ga, curr, _SID, _AUTH, v1bsha)
        v4bsha = v4b['sha']
        self.assertTrue(v4b['merge_needed'])
        curr, naked_get_sha, wip_map = phylesystem.return_study(_SID, commit_sha=v4bsha, return_WIP_map=True)
        self.assertEquals(ac, curr['nexml']["^acount"])
        ac += 1
        curr['nexml']["^acount"] = ac
        ga = phylesystem.create_git_action(_SID)
        v5b = phylesystem.commit_and_try_merge2master(curr, _SID, _AUTH, v3bsha)
        self.assertFalse(v5b['merge_needed'])
        sidl = phylesystem.get_study_ids()
        self.assertIn(_SID, sidl)
        curr, naked_get_sha, wip_map = phylesystem.return_study(_SID, commit_sha=v5b['sha'], return_WIP_map=True)
        self.assertEquals(ac, curr['nexml']["^acount"])
        curr, naked_get_sha, wip_map = phylesystem.return_study(_SID, return_WIP_map=True)
        self.assertEquals(ac, curr['nexml']["^acount"])
        self.assertRaises(KeyError, phylesystem.return_study, _SID, commit_sha=v2bsha, return_WIP_map=True)
        self.assertRaises(KeyError, phylesystem.return_study, _SID, commit_sha=v3bsha, return_WIP_map=True)
        
if __name__ == "__main__":
    unittest.main()
    
