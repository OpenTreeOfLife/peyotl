#! /usr/bin/env python
from peyotl.external import get_ot_study_info_from_treebase_nexml
from peyotl.test.support import pathmap
from peyotl.test.support import equal_blob_check
from peyotl.utility import get_logger
_LOG = get_logger(__name__)
import unittest

# round trip filename tuples
RT_DIRS = ['otu', '9', ]

class TestConvert(unittest.TestCase):
    def testTreeBaseImport(self):
        fp = pathmap.nexml_source_path('S15515.xml')
        n = get_ot_study_info_from_treebase_nexml(src=fp,
                                                  merge_blocks=True,
                                                  sort_arbitrary=True)
        expected = pathmap.nexson_obj('S15515.json')
        equal_blob_check(self, 'S15515', n, expected)
        self.assertTrue(expected == n)
if __name__ == "__main__":
    unittest.main()
