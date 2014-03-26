#! /usr/bin/env python
from peyotl.phylesystem import Phylesystem, _Phylesystem
import unittest
import codecs
import json
from peyotl.test.support import pathmap

class TestPhylesystemMirror(unittest.TestCase):
    def testMirrorConfig(self):
        mi = pathmap.get_test_phylesystem_mirror_info()
        mi['push']['remote_map'] = {'GitHubRemote': 'git@github.com:snacktavish'}
        print mi
        p = _Phylesystem(repos_dict=self.r, mirror_info=mi)

if __name__ == "__main__":
    unittest.main()