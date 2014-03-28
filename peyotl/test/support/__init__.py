#! /usr/bin/env python
from peyotl.utility import get_logger
from peyotl.nexson_syntax import write_as_json
from peyotl.struct_diff import DictDiff
_LOG = get_logger(__name__)

def equal_blob_check(unit_test, diff_file_tag, first, second):
    from peyotl.test.support import pathmap
    if first != second:
        dd = DictDiff.create(first, second)
        ofn = pathmap.next_unique_scratch_filepath(diff_file_tag + '.obtained_rt')
        efn = pathmap.next_unique_scratch_filepath(diff_file_tag + '.expected_rt')
        write_as_json(first, ofn)
        write_as_json(second, efn)
        er = dd.edits_expr()
        _LOG.info('\ndict diff: {d}'.format(d='\n'.join(er)))
        if first != second:
            m_fmt = "TreeBase conversion failed see files {o} and {e}"
            m = m_fmt.format(o=ofn, e=efn)
            unit_test.assertEqual("", m)
