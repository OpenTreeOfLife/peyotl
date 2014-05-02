#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
import unittest
from peyotl import phylesystem


class TestCreate(unittest.TestCase):
    def setUp(self):
        self.reponame = phylesystem.get_repos().keys()[0]
        self.repodir = phylesystem.get_repos()[self.reponame]

    def testConstructor(self):
        gd = GitAction(self.repodir)
        gd.acquire_lock()
        gd.release_lock()
        gd.checkout_master()
        self.assertEqual(gd.current_branch(), "master")

if __name__ == "__main__":
    unittest.main()
