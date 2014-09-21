#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
import unittest
from peyotl import phylesystem
from peyotl.phylesystem import get_repos
try:
    r = get_repos()
    HAS_LOCAL_PHYLESYSTEM_REPOS = True
except:
    HAS_LOCAL_PHYLESYSTEM_REPOS = False


class TestCreate(unittest.TestCase):
    @unittest.skipIf(not HAS_LOCAL_PHYLESYSTEM_REPOS, 'only available if you are have a [phylesystem] section with "parent" variable in your peyotl config')
    def testConstructor(self):
        self.reponame = phylesystem.get_repos().keys()[0]
        self.repodir = phylesystem.get_repos()[self.reponame]
        gd = GitAction(self.repodir)
        gd.acquire_lock()
        gd.release_lock()
        gd.checkout_master()
        self.assertEqual(gd.current_branch(), "master")

if __name__ == "__main__":
    unittest.main()
