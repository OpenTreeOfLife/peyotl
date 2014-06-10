#! /usr/bin/env python
from peyotl.api import OTI
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import sys
import unittest

_LOG = get_logger(__name__)


class TestOTI(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.oti = OTI(d)
    def testFindAllStudies(self):
        x = self.oti.find_all_studies(verbose=True)
        self.assertTrue(len(x) > 0)
        self.assertTrue('ot:studyId' in x[0])
    @unittest.skip("test skipped because OTI's study search appears to be broken. https://github.com/OpenTreeOfLife/oti/issues/19")
    def testStudyTerms(self):
        t_set = self.oti.study_search_term_set
        r = self.oti.find_studies({'ot:studyPublication': '10.1073/pnas.0709121104'})
        print r
    def testNodeTerms(self):
        t_set = self.oti.node_search_term_set
        nl = self.oti.find_nodes(originalLabel='Aponogeoton ulvaceus 1 2')
        self.assertTrue(len(nl) > 0)
        f = nl[0]
        self.assertTrue('matched_trees' in f)
        t = f['matched_trees']
        self.assertTrue(len(t) > 0)
        tr = t[0]
        self.assertTrue('matched_nodes' in tr)
        n = tr['matched_nodes']
        self.assertTrue(len(n) > 0)
    def testBadNodeTerms(self):
        qd = {'bogus key': 'Aponogeoton ulvaceus 1 2'}
        self.assertRaises(ValueError, self.oti.find_nodes, qd)
    def testTreeTerms(self):
        t_set = self.oti.tree_search_term_set
        qd = {'ot:ottTaxonName': 'Aponogeoton ulvaceus'}
        nl = self.oti.find_trees(qd)
        self.assertTrue(len(nl) > 0)
        f = nl[0]
        self.assertTrue('matched_trees' in f)
        t = f['matched_trees']
        self.assertTrue(len(t) > 0)
    def testBadNodeTerms(self):
        qd = {'bogus key': 'Aponogeoton ulvaceus 1 2'}
        self.assertRaises(ValueError, self.oti.find_trees, qd)
if __name__ == "__main__":
    unittest.main(verbosity=5)
