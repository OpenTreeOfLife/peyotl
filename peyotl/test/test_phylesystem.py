#! /usr/bin/env python
from peyotl.phylesystem import Phylesystem, _Phylesystem
import unittest
import codecs
import json
from peyotl.test.support import pathmap

class TestPhylesystem(unittest.TestCase):
    def setUp(self):
        self.r = pathmap.get_test_repos()
    def testInit(self):
        p = _Phylesystem(repos_dict=self.r)
        self.assertEqual(2, len(p._shards))
    def testStudyIndexing(self):
        p = _Phylesystem(repos_dict=self.r)
        k = p._study2shard_map.keys()
        k.sort()
        self.assertEqual(k, ['10', '11', '12', '9'])

if __name__ == "__main__":
    unittest.main()