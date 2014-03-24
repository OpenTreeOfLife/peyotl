#! /usr/bin/env python
from peyotl.phylesystem import Phylesystem
import unittest
import codecs
import json
from peyotl.test.support import pathmap

class TestPhylesystem(unittest.TestCase):
    def testInit(self):
        r = pathmap.get_test_repos()
        p = Phylesystem(r)
        self.assertEqual(2, len(p._shards))
    def testStudyIndexing(self):
        r = pathmap.get_test_repos()
        p = Phylesystem(r)
        k = p._study2shard_map.keys()
        k.sort()
        self.assertEqual(k, ['10', '11', '12', '9'])
if __name__ == "__main__":
    unittest.main()