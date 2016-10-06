#! /usr/bin/env python
from peyotl.api.taxomachine import Taxomachine, TNRSResponse
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)
example_response = {
    u'context': u'All life',
    u'governing_code': u'undefined',
    u'includes_approximate_matches': False,
    u'includes_deprecated_taxa': False,
    u'includes_dubious_names': False,
    u'matched_name_ids': [u'Veronica', u'Homo sapiens'],
    u'results': [{
        u'id': u'Veronica',
        u'matches': [{
            u'flags': [u'EDITED'],
            u'is_approximate_match': False,
            u'is_deprecated': False,
            u'is_dubious': False,
            u'is_synonym': False,
            u'matched_name': u'Veronica',
            u'matched_node_id': 3887636,
            u'nomenclature_code': u'ICN',
            u'ot:ottId': 648853,
            u'ot:ottTaxonName': u'Veronica',
            u'rank': u'',
            u'score': 1.0,
            u'search_string': u'veronica',
            u'synonyms': [
                u'brooklimes',
                u'speedwells',
                u'Diplophyllum',
                u'Beccabunga',
                u'Odicardis',
                u'Macrostemon',
                u'Oligospermum',
                u'Veroncia',
                u'Cochlidiosperma',
                u'Pseudolysimachion',
                u'Veronica'],
            u'unique_name': u'Veronica'}]}, {
            u'id': u'Homo sapiens',
            u'matches': [{
                u'flags': [],
                u'is_approximate_match': False,
                u'is_deprecated': False,
                u'is_dubious': False,
                u'is_synonym': False,
                u'matched_name': u'Homo sapiens',
                u'matched_node_id': 3553897,
                u'nomenclature_code': u'ICZN',
                u'ot:ottId': 770315,
                u'ot:ottTaxonName': u'Homo sapiens',
                u'rank': u'',
                u'score': 1.0,
                u'search_string': u'homo sapiens',
                u'synonyms': [
                    u'Homo palestinus',
                    u'Homo melaninus',
                    u'Homo spelaeus',
                    u'Homo scythicus',
                    u'Homo proto-aethiopicus',
                    u'Homo monstrosus',
                    u'Homo dawsoni',
                    u'Homo cafer',
                    u'Homo eurafricanus',
                    u'Homo helmei',
                    u'man',
                    u'Homo sinicus',
                    u'Homo sapiens',
                    u'Homo cro-magnonensis',
                    u'Homo grimaldii',
                    u'Homo indicus',
                    u'Homo arabicus',
                    u'Homo patagonus',
                    u'Homo aurignacensis',
                    u'Homo drennani',
                    u'Homo troglodytes',
                    u'Homo australasicus',
                    u'Homo japeticus',
                    u'Homo grimaldiensis',
                    u'Homo hottentotus',
                    u'Homo neptunianus',
                    u'Homo hyperboreus',
                    u'Homo americanus',
                    u'human',
                    u'Homo capensis',
                    u'Homo kanamensis',
                    u'Homo columbicus',
                    u'Homo aethiopicus'],
                u'unique_name': u'Homo sapiens'}]}],
    u'taxonomy': {
        u'author': u'open tree of life project',
        u'source': u'ott2.8',
        u'weburl': u'https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-Taxonomy'},
    u'unambiguous_name_ids': [u'Veronica', u'Homo sapiens'],
    u'unmatched_name_ids': [u'Homo sapien']}

@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use '
                 'Open Tree of Life web services are disabled.')
class TestTNRSResponse(unittest.TestCase):
    def testWrap(self):
        #pylint: disable=E1101
        tr = TNRSResponse(None, example_response, {})
        self.assertTrue(tr.context_inferred)
        self.assertIn('Homo sapiens', tr)
        self.assertIn('Homo sapien', tr)
        self.assertEqual(tr['Homo sapien'], tuple())
        self.assertIn('Veronica', tr)
        self.assertIn('source', tr.taxonomy)
        self.assertTrue(tr.taxonomy.source.startswith('ott'))
        self.assertNotIn('Veronic', tr)
        self.assertEqual(tr['Homo sapiens'][0].ott_id, 770315)
        self.assertEqual(tr['Homo sapiens'][0].is_approximate_match, False)
        self.assertFalse(bool(tr['Homo sapien']))

@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use '
                 'Open Tree of Life web services are disabled.')
class TestTaxomachine(unittest.TestCase):
    def setUp(self):
        d = get_test_ot_service_domains()
        self.taxomachine = Taxomachine(d)
    def testTaxon(self):
        if not self.taxomachine.use_v1:
            r = self.taxomachine.taxon(515698, include_lineage=True)
            for k in [u'unique_name', u'taxonomic_lineage', u'rank', u'synonyms',
                      u'ot:ottId', u'flags', u'ot:ottTaxonName', u'node_id']:
                self.assertTrue(k in r)
    def testSubtree(self):
        if not self.taxomachine.use_v1:
            r = self.taxomachine.subtree(515698)
            self.assertTrue(r['subtree'].startswith('('))
    def testLica(self):
        if not self.taxomachine.use_v1:
            r = self.taxomachine.lica([515698, 590452, 409712, 643717], include_lineage=True)
            self.assertTrue('lica' in r)
            self.assertTrue('ott_ids_not_found' in r)
            l = r['lica']
            for k in [u'unique_name', u'taxonomic_lineage', u'rank', u'synonyms',
                      u'ot:ottId', u'flags', u'ot:ottTaxonName', u'node_id']:
                self.assertTrue(k in l)
    def testInfo(self):
        if not self.taxomachine.use_v1:
            cdict = self.taxomachine.info()
            for k in ['source', 'weburl', 'author']:
                self.assertTrue(k in cdict)
    def testContexts(self):
        cdict = self.taxomachine.contexts()
        self.assertTrue('PLANTS' in cdict)
    def testBogusName(self):
        resp = self.taxomachine.TNRS('bogustaxonomicname')
        self.assertEqual(resp['results'], [])
    def testSkunkName(self):
        name = u'Mephitis mephitis'
        resp = self.taxomachine.TNRS(name, 'Mammals')
        self.assertEqual(len(resp['results']), 1)
        el = resp['results'][0]['matches'][0]
        self.assertEqual(el['matched_name'], name)
    def testSkunkNameExact(self):
        name = u'Mephitis mephitis'
        resp = self.taxomachine.TNRS(name, 'Mammals')
        self.assertFalse(resp['results'][0]['matches'][0]['is_approximate_match'])
    def testHomonymName(self):
        name = 'Drosophila'
        resp = self.taxomachine.TNRS(name)
        self.assertEqual(len(resp['results'][0]['matches']), 2)
        resp = self.taxomachine.TNRS(name, 'Animals')
        self.assertEqual(len(resp['results'][0]['matches']), 1)
        resp = self.taxomachine.TNRS(name, 'Fungi')
        self.assertEqual(len(resp['results'][0]['matches']), 1)

if __name__ == "__main__":
    unittest.main(verbosity=5)
