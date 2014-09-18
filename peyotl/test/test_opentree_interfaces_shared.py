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
        write_as_json(content, local_fp, indent=2)


class TestSharedTests(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.ot = APIWrapper(d)

OI_FUNC_TO_PEYOTL = {'gol': 'graph', 'tol': 'tree_of_life'}
for fn in test_files:
    local_fp = os.path.join(shared_tests_par, fn)
    blob = read_as_json(local_fp)
    keys = blob.keys()
    keys.sort()
    for k in keys:
        curr_test = blob[k]
        print k, curr_test['tests'].keys()
        def nf(self, n=k, blob=curr_test):
            oi_name = blob['test_function']
            print oi_name
            s = oi_name.split('_')[0]
            peyotl_meth = '_'.join(oi_name.split('_')[1:])
            trans = OI_FUNC_TO_PEYOTL.get(s, s)
            print 'in test', n, s, trans, peyotl_meth
            wrapper = getattr(self.ot, trans)
            bound_m = getattr(wrapper, peyotl_meth)
            print '    ', bound_m
            response = bound_m(**blob['test_input'])
        setattr(TestSharedTests, k, nf)
if __name__ == "__main__":
    unittest.main()
