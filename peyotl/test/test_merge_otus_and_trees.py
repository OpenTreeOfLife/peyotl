#! /usr/bin/env python
from peyotl.nexson_syntax import write_as_json
from peyotl.manip import merge_otus_and_trees
from peyotl.struct_diff import DictDiff
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)

class TestConvert(unittest.TestCase):
    def _equal_blob_check(self, first, second):
        if first != second:
            dd = DictDiff.create(first, second)
            ofn = pathmap.next_unique_filepath('.obtained_merge_otu')
            efn = pathmap.next_unique_filepath('.expected_merge_otu')
            write_as_json(first, ofn)
            write_as_json(second, efn)
            er = dd.edits_expr()
            _LOG.info('\ndict diff: {d}'.format(d='\n'.join(er)))
            if first != second:
                self.assertEqual("", "merge_otus_and_tree failed see files {o} and {e}".format(o=ofn, e=efn))
    def testCanConvert(self):
        inp = pathmap.nexson_obj('merge/merge-input.v1.0.json')
        expected = pathmap.nexson_obj('merge/merge-expected.v1.0.json')
        self.assertNotEqual(inp, expected)
        merge_otus_and_trees(inp)
        self._equal_blob_check(inp, expected)

if __name__ == "__main__":
    unittest.main()
