#! /usr/bin/env python
from peyotl.nexson_syntax import can_convert_nexson_forms, \
                                 convert_nexson_format, \
                                 get_ot_study_info_from_treebase_nexml, \
                                 sort_meta_elements, \
                                 sort_arbitrarily_ordered_nexson, \
                                 write_as_json, \
                                 BY_ID_HONEY_BADGERFISH
from peyotl.nexson_validation import validate_nexson
from peyotl.struct_diff import DictDiff
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)

# round trip filename tuples
RT_DIRS = ['otu', '9', ]

def _get_pair(par, f, s):
    bf = os.path.join(par, f)
    hbf = os.path.join(par, s)
    fp, sp = pathmap.nexson_source_path(bf), pathmap.nexson_source_path(hbf)
    if not os.path.exists(fp):
        _LOG.warn('\nTest skipped because {s} does not exist'.format(s=fp))
        return None, None
    if not os.path.exists(sp):
        _LOG.warn('\nTest skipped because {s} does not exist'.format(s=sp))
        return None, None
    return pathmap.nexson_obj(bf), pathmap.nexson_obj(hbf)

class TestConvert(unittest.TestCase):
    def _equal_blob_check(self, first, second):
        if first != second:
            dd = DictDiff.create(first, second)
            ofn = pathmap.next_unique_scratch_filepath('.obtained_rt')
            efn = pathmap.next_unique_scratch_filepath('.expected_rt')
            write_as_json(first, ofn)
            write_as_json(second, efn)
            er = dd.edits_expr()
            _LOG.info('\ndict diff: {d}'.format(d='\n'.join(er)))
            if first != second:
                self.assertEqual("", "Roundtrip failed see files {o} and {e}".format(o=ofn, e=efn))
    def testTreeBaseImport(self):
        fp = pathmap.nexml_source_path('S15515.xml')
        n = get_ot_study_info_from_treebase_nexml(src=fp,
                                                  merge_blocks=True,
                                                  sort_arbitrary=True)
        aa = validate_nexson(n)
        annot = aa[0]
        ew_dict = annot.get_err_warn_summary_dict()
        #import sys; write_as_json(n, sys.stdout);write_as_json(ew_dict, sys.stdout)
        self.assertFalse(annot.has_error())
if __name__ == "__main__":
    unittest.main()
