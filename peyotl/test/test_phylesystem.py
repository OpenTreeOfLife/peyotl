#! /usr/bin/env python
from peyotl.phylesystem import Phylesystem
import unittest
import codecs
import json
from peyotl.nexson_syntax import read_as_json
from peyotl.test.support import pathmap

class TestPhylesystem(unittest.TestCase):
    def testInit(self):
        r = pathmap.get_test_repos()
        p = Phylesystem(r)
        self.assertEqual(2, len(p._shards))

if __name__ == "__main__":
    unittest.main()