#! /usr/bin/env python
import os
import unittest

from peyotl.api import APIWrapper
from peyotl.test.support import example_ott_id_list
from peyotl.test.support import test_phylesystem_api_for_study, test_tol_about
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
from requests.exceptions import HTTPError

_LOG = get_logger(__name__)


@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use '
                 'Open Tree of Life web services are disabled.')
class TestV2Facade(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.ot = APIWrapper(d)

    def testFindAllStudies(self):
        x = self.ot.studies.find_studies(verbose=True)
        self.assertTrue(len(x) > 0)
        self.assertTrue('ot:studyId' in x[0])

    def testStudyTerms(self):
        t_set = self.ot.studies.properties()
        self.assertTrue(bool(t_set))
        r = self.ot.studies.find_studies({'ot:studyPublication': '10.1073/pnas.0709121104'})
        self.assertTrue(len(r) > 0)

    def testTaxon(self):
        r = self.ot.taxonomy.taxon(515698, include_lineage=True)
        for k in [u'unique_name', u'taxonomic_lineage', u'rank',
                  u'synonyms', u'ot:ottId', u'flags', u'ot:ottTaxonName', u'node_id']:
            self.assertTrue(k in r)

    def testSubtree(self):
        r = self.ot.taxonomy.subtree(515698)
        self.assertTrue(r['subtree'].startswith('('))

    def testLica(self):
        r = self.ot.taxonomy.lica([515698, 590452, 409712, 643717], include_lineage=True)
        self.assertTrue('lica' in r)
        self.assertTrue('ott_ids_not_found' in r)
        l = r['lica']
        for k in [u'unique_name', u'taxonomic_lineage', u'rank',
                  u'synonyms', u'ot:ottId', u'flags', u'ot:ottTaxonName', u'node_id']:
            self.assertTrue(k in l)

    def testInfo(self):
        cdict = self.ot.taxonomy.info()
        for k in ['source', 'weburl', 'author']:
            self.assertTrue(k in cdict)

    def testContexts(self):
        cdict = self.ot.tnrs.contexts()
        self.assertTrue('PLANTS' in cdict)

    def testBogusName(self):
        resp = self.ot.tnrs.match_names('bogustaxonomicname')
        self.assertEqual(resp['results'], [])

    def testSkunkName(self):
        name = u'Mephitis mephitis'
        resp = self.ot.tnrs.match_names(name, 'Mammals')
        self.assertEqual(len(resp['results']), 1)
        el = resp['results'][0]['matches'][0]
        self.assertEqual(el['matched_name'], name)

    def testSkunkNameExact(self):
        name = u'Mephitis mephitis'
        resp = self.ot.tnrs.match_names(name, 'Mammals')
        self.assertFalse(resp['results'][0]['matches'][0]['is_approximate_match'])

    def testHomonymName(self):
        name = 'Drosophila'
        resp = self.ot.tnrs.match_names(name)
        self.assertEqual(len(resp['results'][0]['matches']), 2)
        resp = self.ot.tnrs.match_names(name, 'Animals')
        self.assertEqual(len(resp['results'][0]['matches']), 1)
        resp = self.ot.tnrs.match_names(name, 'Fungi')
        self.assertEqual(len(resp['results'][0]['matches']), 1)

    def testSourceTree(self):
        source_id_list = self.ot.tree_of_life.about()['study_list']
        self.assertTrue(isinstance(source_id_list, list))
        # commented out due to https://github.com/OpenTreeOfLife/treemachine/issues/170
        # f = source_id_list[0]
        # r = self.ot.graph.source_tree(**f)
        # self.assertTrue(r['newick'].startswith('('))

    def testSynthTree(self):
        cdict = self.ot.tree_of_life.about()
        tree_id, node_id = test_tol_about(self, cdict)
        # this service is no longer supported, so returns an HTTPError
        self.assertRaises(HTTPError, self.ot.tree_of_life.subtree, tree_id, format='newick', node_id=node_id)

    def testPrunedTree(self):
        r = self.ot.tree_of_life.induced_subtree(ott_ids=example_ott_id_list)
        for key in ['ott_ids_not_in_tree', u'node_ids_not_in_tree']:
            self.assertEqual(r[key], [])
        self.assertTrue(r['newick'].startswith('('))

    def testMRCA(self):
        r = self.ot.tree_of_life.mrca(ott_ids=example_ott_id_list)
        self.assertTrue('mrca_node_id' in r)

    def testStudy(self):
        test_phylesystem_api_for_study(self, self.ot.study)


if __name__ == "__main__":
    unittest.main()
