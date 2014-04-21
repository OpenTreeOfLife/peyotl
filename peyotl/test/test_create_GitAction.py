#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
import unittest
from peyotl import phylesystem

reponame = phylesystem.get_repos().keys()[0]
repodir = phylesystem.get_repos()[reponame]

class TestCreate(unittest.TestCase):
    def testConstructor(self):
        gd = GitAction(repodir)
        gd.acquire_lock()
        gd.release_lock()
        gd.checkout_master()
        self.assertEqual(gd.current_branch(), "master")

if __name__ == "__main__":
    unittest.main()
