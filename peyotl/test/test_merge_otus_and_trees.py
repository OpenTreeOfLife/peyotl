#! /usr/bin/env python
from peyotl.nexson_syntax import sort_arbitrarily_ordered_nexson
from peyotl.manip import merge_otus_and_trees
from peyotl.test.support import pathmap
from peyotl.test.support import equal_blob_check
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)

class TestMerge(unittest.TestCase):
    def testCanConvert(self):
        inp = pathmap.nexson_obj('merge/merge-input.v1.2.json')
        expected = pathmap.nexson_obj('merge/merge-expected.v1.2.json')
        expected = sort_arbitrarily_ordered_nexson(expected)
        inp = sort_arbitrarily_ordered_nexson(inp)
        self.assertNotEqual(inp, expected)
        merge_otus_and_trees(inp)
        equal_blob_check(self, '', inp, expected)

if __name__ == "__main__":
    unittest.main()
