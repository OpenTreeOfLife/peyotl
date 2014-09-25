#!/usr/bin/env python
from peyotl.test.support.pathmap import get_test_ot_service_domains, \
                                        shared_test_dir
from peyotl.nexson_syntax import read_as_json
from peyotl.api import APIWrapper
from peyotl.utility import get_logger
import subprocess
import unittest
import os
prefix = 'https://raw.githubusercontent.com/OpenTreeOfLife/opentree-interfaces/master/python/test'
test_files = ['tree_of_life.json', 'graph_of_life.json', 'tnrs.json', 'taxonomy.json']

_LOG = get_logger(__name__)
shared_tests_par = shared_test_dir()
if not os.path.exists(shared_tests_par):
    shared_test_grandpar = os.path.split(shared_tests_par)[0]
    _LOG.debug('cloning shared-api-tests dir "{}"'.format(shared_test_grandpar))
    invoc = ['git', 'clone', 'https://github.com/OpenTreeOfLife/shared-api-tests']
    _LOG.debug('cloning invoc "{}"'.format(repr(invoc)))
    git_clone = subprocess.Popen(invoc, cwd=shared_test_grandpar)
    assert 0 == git_clone.wait()



class TestSharedTests(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.ot = APIWrapper(d)
STOP = False
OI_FUNC_TO_PEYOTL = {'gol': 'graph', 'tol': 'tree_of_life'}
_EXC_STR_TO_EXC_CLASS = {'ValueError': ValueError,
                         'KeyError': KeyError,
                         'OpenTreeService.OpenTreeError': Exception,}
_TYPE_MAP = {'dict': dict}
if not os.path.exists(shared_tests_par):
    _LOG.debug('skipping shared tests due to lack of "{}" dir'.format(shared_tests_par))
else:
    update_shared_tests = True
    if update_shared_tests:
        _LOG.debug('updating shared-api-tests dir "{}"'.format(shared_tests_par))
        git_pull = subprocess.Popen(['git', 'pull', 'origin', 'master'],
                                      cwd=shared_tests_par)
        try:
            git_pull.wait()
        except:
            pass # we want the pass to test when we are offline...
    for fn in test_files:
        local_fp = os.path.join(shared_tests_par, fn)
        tblob = read_as_json(local_fp)
        keys = tblob.keys()
        keys.sort()
        for k in keys:
            curr_test = tblob[k]
            #print k, curr_test['tests'].keys()
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
                #print '    in', n, ' Calling', bound_m, 'with', args
                try:
                    if ('parameters_error' in expected) or ('contains_error' in expected):
                        ec = expected.get('parameters_error')
                        if ec is None:
                            ec = expected['contains_error']
                            et = Exception
                        else:
                            exc_class = ec[0]
                            et = _EXC_STR_TO_EXC_CLASS[exc_class]
                        #print args
                        self.assertRaises(et, bound_m, **args)
                    else:
                        response = bound_m(**args)
                        key_list = ['contains', 'deep_equals', 'equals', 'of_type']
                        #_LOG.debug('kl = ' + str(expected.keys()))
                        for ek in expected.keys():
                            assert ek in key_list
                        for ek in key_list:
                            tests4k = expected.get(ek, [])
                            if ek == 'contains':
                                for t in tests4k:
                                    ec, em = t
                                    self.assertTrue(ec in response, em)
                            elif ek == 'deep_equals':
                                for t in tests4k:
                                    ec, em = t
                                    rkey_list, rexp = ec
                                    curr = response
                                    while rkey_list:
                                        nk = rkey_list.pop(0)
                                        curr = curr[nk]
                                    self.assertEqual(curr, rexp, em)
                            elif ek == 'equals':
                                for t in tests4k:
                                    ec, em = t
                                    rkey, rexp = ec
                                    self.assertEqual(response[rkey], rexp, em)
                            elif tests4k:
                                assert ek == 'of_type'
                                #_LOG.debug('tests4k = {}'.format(repr(tests4k)))
                                ec, em = tests4k
                                py_typ = _TYPE_MAP[ec]
                                self.assertTrue(isinstance(response, py_typ), em)
                except:
                    STOP = True
                    _LOG.exception('failed!')
            setattr(TestSharedTests, k, nf)
if __name__ == "__main__":
    unittest.main()
