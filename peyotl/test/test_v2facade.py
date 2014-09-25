#! /usr/bin/env python
from peyotl.api import APIWrapper
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.nexson_syntax.helper import detect_nexson_version, find_val_literal_meta_first
from peyotl.utility import get_logger
import sys
import unittest

_LOG = get_logger(__name__)

class TestOTI(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.ot = APIWrapper(d)
    def testFindAllStudies(self):
        x = self.ot.studies.find_studies(verbose=True)
        self.assertTrue(len(x) > 0)
        self.assertTrue('ot:studyId' in x[0])
    def testStudyTerms(self):
        t_set = self.ot.studies.properties()
        r = self.ot.studies.find_studies({'ot:studyPublication': '10.1073/pnas.0709121104'})
        self.assertTrue(len(r) > 0)
    def testTaxon(self):
        r = self.ot.taxonomy.taxon(515698, include_lineage=True)
        for k in [u'unique_name', u'taxonomic_lineage', u'rank', u'synonyms', u'ot:ottId', u'flags', u'ot:ottTaxonName', u'node_id']:
            self.assertTrue(k in r)
    def testSubtree(self):
        r = self.ot.taxonomy.subtree(515698)
        self.assertTrue(r['subtree'].startswith('('))
    def testLica(self):
        r = self.ot.taxonomy.lica([515698, 590452, 409712, 643717], include_lineage=True)
        self.assertTrue('lica' in r)
        self.assertTrue('ott_ids_not_found' in r)
        l = r['lica']
        for k in [u'unique_name', u'taxonomic_lineage', u'rank', u'synonyms', u'ot:ottId', u'flags', u'ot:ottTaxonName', u'node_id']:
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
        name = 'Nandina'
        resp = self.ot.tnrs.match_names(name)
        self.assertEqual(len(resp['results'][0]['matches']), 2)
        resp = self.ot.tnrs.match_names(name, 'Animals')
        self.assertEqual(len(resp['results'][0]['matches']), 1)
        resp = self.ot.tnrs.match_names(name, 'Flowering plants')
        self.assertEqual(len(resp['results'][0]['matches']), 1)
    def testSourceTree(self):
        source_id_list = self.ot.tree_of_life.about()['study_list']
        self.assertTrue(isinstance(source_id_list, list))
        f = source_id_list[0]
        r = self.ot.graph.source_tree(**f)
        self.assertTrue(r['newick'].startswith('('))
    def testSynthTree(self):
        cdict = self.ot.tree_of_life.about()
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
        node_id = str(cdict['root_node_id']) # Odd that this is a string
        self.assertRaises(ValueError, self.ot.tree_of_life.subtree, tree_id, format='newick', node_id=node_id)
    def testPrunedTree(self):
        ott_ids = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579, 267484, 128308, 380453, 678579, 883864, 863991, 3898562, 23821, 673540, 122251, 106729, 1084532, 541659]
        r = self.ot.tree_of_life.induced_subtree(ott_ids=ott_ids)
        for key in ['ott_ids_not_in_tree', u'node_ids_not_in_tree']:
            self.assertEqual(r[key], [])
        self.assertTrue(r['subtree'].startswith('('))
    def testMRCA(self):
        ott_ids = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579, 267484, 128308, 380453, 678579, 883864, 863991, 3898562, 23821, 673540, 122251, 106729, 1084532, 541659]
        r = self.ot.tree_of_life.mrca(ott_ids=ott_ids)
        self.assertTrue('mrca_node_id' in r)
    def testStudy(self):
        x = self.ot.study.get('pg_10')['data']
        sid = find_val_literal_meta_first(x['nexml'], 'ot:studyId', detect_nexson_version(x))
        self.assertTrue(sid in ['10', 'pg_10'])
        y = self.ot.study.get('pg_10', tree_id='tree3', format='newick')
        self.assertTrue(y.startswith('('))

if __name__ == "__main__":
    unittest.main()
