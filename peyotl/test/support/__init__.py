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

example_ott_id_list = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579,
                   267484, 128308, 380453, 678579, 883864, 5537065,
                   3898562, 5507605, 673540, 122251, 5507740, 1084532, 541659]

def test_phylesystem_api_for_study(test_case_instance, phylesystem_wrapper, study_id='pg_10'):
    from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
    x = phylesystem_wrapper.get(study_id)['data']
    sid = find_val_literal_meta_first(x['nexml'], 'ot:studyId', detect_nexson_version(x))
    test_case_instance.assertTrue(sid in [study_id])
    y = phylesystem_wrapper.get(study_id, tree_id='tree3', format='newick')
    test_case_instance.assertTrue(y.startswith('('))
