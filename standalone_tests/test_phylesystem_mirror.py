#! /usr/bin/env python
from peyotl.phylesystem import Phylesystem, _Phylesystem
import unittest
import codecs
import json
from peyotl.test.support import pathmap

class TestPhylesystemMirror(unittest.TestCase):
    def testMirrorConfig(self):
        p = pathmap.get_test_phylesystem()
if __name__ == "__main__":
    unittest.main()