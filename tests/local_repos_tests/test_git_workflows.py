#! /usr/bin/env python
from peyotl.git_storage.git_workflow import acquire_lock_raise, merge_from_master
from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, GitWorkflowError
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.utility import get_logger, get_raw_default_config_and_read_file_list
from peyotl.utility.get_config import _replace_default_config
import unittest
import json
import copy
import sys
from peyotl.test.support import get_test_path_mapper

pathmap = get_test_path_mapper()

_LOG = get_logger(__name__)

config, cfg_filename = get_raw_default_config_and_read_file_list()
COMMITS_SHOULD_FAIL_ARG = 'tiny_max_file_size'
COMMITS_SHOULD_FAIL = COMMITS_SHOULD_FAIL_ARG in sys.argv
if COMMITS_SHOULD_FAIL:
    sys.argv.remove(COMMITS_SHOULD_FAIL_ARG)
    if 'phylesystem' not in config.sections():
        config.add_section('phylesystem')
    config.set('phylesystem', 'max_file_size', '10')  # ten bytes is not large
_replace_default_config(config)

phylesystem = Phylesystem(pathmap.get_test_repos())

_MINI_PHYL_SHA1 = 'c281fb7e1cdf9cfdb29bb151ac7e1ad9d1d7036e'
_SID = 'xy_10'
_AUTH = {
    'name': 'test_name',
    'email': 'test_email@example.org',
    'login': 'test_gh_login',
}


def aco_log(obj, tag):
    nex = obj['nexml']
    _LOG.debug('{}[acount]={} +[zcount]={}'.format(tag, nex.get('^acount'), nex.get('^zcount')))

class TestPhylesystem(unittest.TestCase):
    def testObjectSHA(self):
        ga = phylesystem.create_git_action(_SID)
        ga.acquire_lock()
        try:
            obj_sha = ga.object_SHA(_SID, commit_sha=_MINI_PHYL_SHA1)
        finally:
            ga.release_lock()
        self.assertEqual(obj_sha, 'eacda27eae0ea2947ecb97b0b646e2dc5707e70c')

    def testSimple(self):
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
        try:
            commit_and_try_merge2master(ga, curr_obj, _SID, _AUTH, sha)
        except GitWorkflowError:
            if not COMMITS_SHOULD_FAIL:
                raise

    def testBranched(self):
        ga = phylesystem.create_git_action(_SID)
        ga.acquire_lock()
        try:
            curr, sha, wip_map = ga.return_study(_SID, return_WIP_map=True)
        finally:
            ga.release_lock()
        _LOG.debug('test sha = "{}"'.format(sha))
        self.assertEqual(list(wip_map.keys()), ['master'])
        acurr_obj = json.loads(curr)
        # aco_log(acurr_obj, '1. acurr_obj')
        zcurr_obj = copy.deepcopy(acurr_obj)
        ac = acurr_obj['nexml'].get("^acount", 0)
        # add a second commit that should merge to master
        ac += 1
        acurr_obj['nexml']["^acount"] = ac
        # aco_log(acurr_obj, '2. acurr_obj')
        try:
            v1b = commit_and_try_merge2master(ga, acurr_obj, _SID, _AUTH, sha)
        except GitWorkflowError:
            if not COMMITS_SHOULD_FAIL:
                raise
            return
        self.assertFalse(v1b['merge_needed'])

        # add a third commit that should NOT merge to master
        zc = zcurr_obj['nexml'].get("^zcount", 0)
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        # aco_log(zcurr_obj, '2b. zcurr_obj')
        v2b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, sha)

        self.assertNotEqual(v1b['branch_name'], v2b['branch_name'])
        self.assertNotEqual(v1b['sha'], v2b['sha'])
        self.assertEqual(v1b['sha'], ga.get_master_sha())  # not locked!
        self.assertTrue(v2b['merge_needed'])

        # fetching studies (GETs in the API) should report 
        # the existence of multiple branches for this study...
        ga.acquire_lock()
        try:
            t, ts, wip_map = ga.return_study(_SID, return_WIP_map=True)
        finally:
            ga.release_lock()
        self.assertEqual(wip_map['master'], v1b['sha'])
        self.assertEqual(wip_map['test_gh_login_study_{}_0'.format(_SID)], v2b['sha'])

        # but not for other studies...
        ga.acquire_lock()
        try:
            t, ts, wip_map = ga.return_study('xy_13', return_WIP_map=True)
        finally:
            ga.release_lock()
        self.assertEqual(wip_map['master'], v1b['sha'])
        self.assertEqual(list(wip_map.keys()), ['master'])

        # add a fourth commit onto commit 2. This should merge to master
        ac += 1
        acurr_obj['nexml']["^acount"] = ac
        # aco_log(acurr_obj, '3b. acurr_obj')
        v3b = commit_and_try_merge2master(ga, acurr_obj, _SID, _AUTH, v1b['sha'])
        self.assertFalse(v3b['merge_needed'])

        # add a fifth commit onto commit 3. This should still NOT merge to master
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        # aco_log(zcurr_obj, '4b. zcurr_obj')
        v4b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, v2b['sha'])

        self.assertNotEqual(v3b['branch_name'], v4b['branch_name'])
        self.assertEqual(v2b['branch_name'], v4b['branch_name'])
        self.assertNotEqual(v3b['sha'], v4b['sha'])
        self.assertEqual(v3b['sha'], ga.get_master_sha())  # not locked!
        self.assertTrue(v4b['merge_needed'])

        # sixth commit is the merge
        mblob = merge_from_master(ga, _SID, _AUTH, v4b['sha'])
        self.assertEqual(mblob["error"], 0)
        self.assertEqual(mblob["resource_id"], _SID)

        # add a 7th commit onto commit 6. This should NOT merge to master because we don't give it the secret arg.
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        # aco_log(zcurr_obj, '5b. zcurr_obj')
        v5b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, mblob['sha'])
        self.assertNotEqual(v3b['sha'], v5b['sha'])
        self.assertTrue(v5b['merge_needed'])

        # add a 7th commit onto commit 6. This should merge to master because we provide the merged SHA
        zc += 1
        zcurr_obj['nexml']["^zcount"] = zc
        v6b = commit_and_try_merge2master(ga, zcurr_obj, _SID, _AUTH, v5b['sha'], merged_sha=mblob['merged_sha'])
        self.assertNotEqual(v3b['sha'], v6b['sha'])
        self.assertEqual(v6b['sha'], ga.get_master_sha())  # not locked!
        self.assertFalse(v6b['merge_needed'])
        self.assertEqual(v6b['branch_name'], 'master')

        # after the merge we should be back down to 1 branch for this study
        ga.acquire_lock()
        try:
            t, ts, wip_map = ga.return_study(_SID, return_WIP_map=True)
        finally:
            ga.release_lock()
        self.assertEqual(list(wip_map.keys()), ['master'])


if __name__ == "__main__":
    unittest.main()
