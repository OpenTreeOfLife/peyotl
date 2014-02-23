#! /usr/bin/env python
from peyotl.manip import count_num_trees
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)

class TestManip(unittest.TestCase):
    def testCanCountTrees(self):
        for v in ['0.0', '1.0', '1.2']:
            inp = pathmap.nexson_obj('otu/v{v}.json'.format(v=v))
            self.assertEqual(1, count_num_trees(inp, v))

if __name__ == "__main__":
    unittest.main()
