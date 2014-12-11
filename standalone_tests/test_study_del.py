#! /usr/bin/env python
from peyotl.phylesystem.git_workflows import acquire_lock_raise, \
                                             commit_and_try_merge2master, \
                                             delete_study, \
                                             GitWorkflowError, \
                                             merge_from_master
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
        ac += 1
        acurr_obj['nexml']["^acount"] = ac
        v1b = commit_and_try_merge2master(ga, acurr_obj, _SID, _AUTH, sha)
        self.assertFalse(v1b['merge_needed'])
        sidl = phylesystem.get_study_ids()
        self.assertIn(_SID, sidl)
        v2b = phylesystem.delete_study(_SID, _AUTH, sha)
        self.assertTrue(v2b['merge_needed'])
        sidl = phylesystem.get_study_ids()
        self.assertIn(_SID, sidl)
        curr, naked_get_sha, wip_map = ga.return_study(_SID, return_WIP_map=True)
        self.assertEquals(naked_get_sha, v1b['sha'])
        v2b = phylesystem.delete_study(_SID, _AUTH, naked_get_sha)
        sidl = phylesystem.get_study_ids()
        self.assertNotIn(_SID, sidl)
        

if __name__ == "__main__":
    unittest.main()
    