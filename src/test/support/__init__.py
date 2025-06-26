#! /usr/bin/env python
from peyotl.utility import get_logger
from peyotl.nexson_syntax import write_as_json
from peyotl.struct_diff import DictDiff

_LOG = get_logger(__name__)

from .pathmap import get_test_path_mapper


example_ott_id_list = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579,
                       267484, 128308, 380453, 678579, 883864, 5537065,
                       3898562, 5507605, 673540, 122251, 5507740, 1084532, 541659]


def test_phylesystem_api_for_study(test_case_instance, phylesystem_wrapper, study_id='pg_10'):
    from peyotl.nexson_syntax import detect_nexson_version, find_val_literal_meta_first
    x = phylesystem_wrapper.get(study_id)['data']
    sid = find_val_literal_meta_first(x['nexml'], 'ot:studyId', detect_nexson_version(x))
    test_case_instance.assertTrue(sid in [study_id])
    y = phylesystem_wrapper.get(study_id, tree_id='tree3', format='newick')
    test_case_instance.assertTrue(y.startswith('('))


def test_amendments_api(test_case_instance, amendments_wrapper):
    try:
        a = amendments_wrapper.get('additions-5000000-5000003')
        cn = a['study_id']
        test_case_instance.assertTrue(cn in [u'ot_234', ])
    except:
        # try alternate amendments (and study_id) for remote/proxied docstores
        try:
            # this is an amendment in the production repo!
            a = amendments_wrapper.get('additions-5861452-5861452')
            cn = a['study_id']
            test_case_instance.assertTrue(cn in [u'ot_520', ])
        except:
            # this is an amendment in the devapi repo (amendments-0)!
            a = amendments_wrapper.get('additions-10000000-10000001')
            cn = a['study_id']
            test_case_instance.assertTrue(cn in [u'pg_2606', ])


def test_collections_api(test_case_instance, collections_wrapper):
    try:
        c = collections_wrapper.get('TestUserB/my-favorite-trees')
    except:
        # alternate collection for remote/proxied docstore
        c = collections_wrapper.get('jimallman/my-test-collection')
    cn = c['name']
    test_case_instance.assertTrue(cn in [u'My favorite trees!', u'My test collection'])


def raise_http_error_with_more_detail(err):
    # show more useful information (JSON payload) from the server
    details = err.response.text
    raise ValueError("{e}, details: {m}".format(e=err, m=details))


def test_tol_about(self, cdict):
    for key in [u'date',
                u'num_source_studies',
                u'root_taxon_name',
                u'study_list',
                u'root_ott_id',
                u'root_node_id',
                u'tree_id',
                u'taxonomy_version',
                u'num_tips']:
        self.assertTrue(key in cdict)
    tree_id = cdict['tree_id']
    node_id = str(cdict['root_node_id'])  # Odd that this is a string
    return tree_id, node_id
