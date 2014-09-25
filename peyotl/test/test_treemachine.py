#! /usr/bin/env python
from peyotl.nexson_syntax import write_as_json
from peyotl.api import Treemachine, Taxomachine
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest

_LOG = get_logger(__name__)

class TestTreemachine(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()
        self.treemachine = Treemachine(self.domains)
    def testSourceTree(self):
        source_id_list = self.treemachine.get_synthetic_tree_id_list()
        self.assertTrue(isinstance(source_id_list, list))
        f = source_id_list[0]
        r = self.treemachine.get_source_tree(**f)
        self.assertTrue(r['newick'].startswith('('))
    def testSynthTree(self):
        cdict = self.treemachine.get_synthetic_tree_info()
        if self.treemachine.use_v1:
            for key in ['draftTreeName', 'startNodeTaxName', 'startNodeID', 'startNodeOTTId']:
                self.assertTrue(key in cdict)
                tree_id = cdict['draftTreeName']
                node_id = str(cdict['startNodeID']) # Odd that this is a string
                x = self.treemachine.get_synthetic_tree(tree_id,
                                                        format='newick',
                                                        node_id=node_id,
                                                        max_depth=2)
                self.assertEqual(x['treeID'], tree_id)
                self.assertTrue(x['newick'].startswith('('))
        else:
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
            self.assertRaises(ValueError, self.treemachine.get_synthetic_tree, tree_id, format='newick', node_id=node_id)
    def testPrunedTree(self):
        ott_ids = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579, 267484, 128308, 380453, 678579, 883864, 863991, 3898562, 23821, 673540, 122251, 106729, 1084532, 541659]
        if self.treemachine.use_v1:
            r = self.treemachine.get_synth_tree_pruned(ott_ids=ott_ids)
            self.assertEqual(len(ott_ids), len(r['found_nodes']))
        else:
            r = self.treemachine.induced_subtree(ott_ids=ott_ids)
            for key in ['ott_ids_not_in_tree', u'node_ids_not_in_tree']:
                self.assertEqual(r[key], [])
        self.assertTrue(r['subtree'].startswith('('))
    def testMRCA(self):
        ott_ids = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579, 267484, 128308, 380453, 678579, 883864, 863991, 3898562, 23821, 673540, 122251, 106729, 1084532, 541659]
        if not self.treemachine.use_v1:
            r = self.treemachine.mrca(ott_ids=ott_ids)
            self.assertTrue('mrca_node_id' in r)
            print 'node_info is', self.treemachine.node_info(r['mrca_node_id'])
class Skip:
    def testSearchForTaxon(self):
        taxomachine = Taxomachine(self.domains)
        anolis_taxon = taxomachine.autocomplete('Anolis')
        ottId = anolis_taxon[0]['ottId']
        node_id = self.treemachine.get_node_id_for_ott_id(ottId)
        x = self.treemachine.get_synthetic_tree(format='newick', node_id=node_id, max_depth=12)
        #print '{};'.format(x['newick'])

if __name__ == "__main__":
    unittest.main()
