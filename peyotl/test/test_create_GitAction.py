#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
import unittest

repodir="/Users/ejmctavish/Documents/projects/otapi/phylesystem_test"

class TestCreate(unittest.TestCase):
        gd=GitAction(repodir)
        gd.acquire_lock()
        gd.release_lock()
        gd.checkout_master()
        assert(gd.current_branch()=="master")
        
if __name__ == "__main__":
    unittest.main()
