#!/usr/bin/env python
from peyotl.test.support.pathmap import get_test_ot_service_domains, \
                                        shared_test_dir
from peyotl.nexson_syntax.helper import detect_nexson_version
from peyotl.nexson_syntax import read_as_json, write_as_json
from peyotl.api import APIWrapper
from peyotl.utility import get_logger
import unittest
import requests
import json
import sys
import os
prefix = 'https://raw.githubusercontent.com/OpenTreeOfLife/opentree-interfaces/master/python/test'
test_files = ['tree_of_life.json', 'graph_of_life.json', 'tnrs.json', 'taxonomy.json']

_LOG = get_logger(__name__)
shared_tests_par = shared_test_dir()
if not os.path.exists(shared_tests_par):
    os.mkdir(shared_tests_par)

update_shared_tests = False
if update_shared_tests:
    for fn in test_files:
        content = requests.get(prefix + '/' + fn).json()
        local_fp = os.path.join(shared_tests_par, fn)
        write_as_json(content, local_fp, indent=4)


class TestSharedTests(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.ot = APIWrapper(d)
STOP = False
OI_FUNC_TO_PEYOTL = {'gol': 'graph', 'tol': 'tree_of_life'}
_EXC_STR_TO_EXC_CLASS = {'ValueError': ValueError,
                         'KeyError': KeyError,
                         'OpenTreeService.OpenTreeError': Exception,}
if False:#TEMP #TODO
#for fn in test_files:
    local_fp = os.path.join(shared_tests_par, fn)
    blob = read_as_json(local_fp)
    keys = blob.keys()
    keys.sort()
    for k in keys:
        curr_test = blob[k]
        print k, curr_test['tests'].keys()
        def nf(self, n=k, blob=curr_test):
            global STOP
            if STOP or n == 'test_subtree_demo':
                return
            oi_name = blob['test_function']
            expected = blob['tests']
            s = oi_name.split('_')[0]
            peyotl_meth = '_'.join(oi_name.split('_')[1:])
            trans = OI_FUNC_TO_PEYOTL.get(s, s)
            wrapper = getattr(self.ot, trans)
            bound_m = getattr(wrapper, peyotl_meth)
            args = blob['test_input']
            try:
                if args == 'null':
                    args = {}
            except:
                pass
            print '    in', n, ' Calling', bound_m, 'with', args
            try:
                if 'error' in expected:
                    exc_class = expected['error'][0][0]
                    et = _EXC_STR_TO_EXC_CLASS[exc_class]
                    print args
                    self.assertRaises(et, bound_m, **args)
                else:
                    response = bound_m(**args)
                    key_list = ['contains', 'equals', 'of_type']
                    for k in expected.keys():
                        assert k in key_list
                    for k in key_list:
                        tests4k = expected.get(k, [])
                        if k == 'contains':
                            for t in tests4k:
                                ec, em = t
                                self.assertTrue(ec in response, em)
            except:
                STOP = True
                _LOG.exception('failed!')
        setattr(TestSharedTests, k, nf)
if __name__ == "__main__":
    unittest.main()
