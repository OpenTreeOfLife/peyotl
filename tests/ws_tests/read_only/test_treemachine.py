#! /usr/bin/env python
from __future__ import absolute_import, print_function, division
from peyotl.api import Treemachine, Taxomachine
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.test.support import example_ott_id_list
from peyotl.test.support import test_tol_about
from peyotl.utility import get_logger
from requests.exceptions import HTTPError
import unittest
import os

_LOG = get_logger(__name__)


# pylint: disable=W0713
@unittest.skipIf('RUN_WEB_SERVICE_TESTS' not in os.environ,
                 'RUN_WEB_SERVICE_TESTS is not in your environment, so tests that use '
                 'Open Tree of Life web services are disabled.')
class TestTreemachine(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()
        self.treemachine = Treemachine(self.domains)

    def testSourceTree(self):
        source_id_list = self.treemachine.synthetic_tree_id_list
        self.assertTrue(isinstance(source_id_list, list))
        # commented out due to https://github.com/OpenTreeOfLife/treemachine/issues/170
        # f = source_id_list[0]
        # r = self.treemachine.get_source_tree(**f)
        # self.assertTrue(r['newick'].startswith('('))

    def testSynthTree(self):
        cdict = self.treemachine.synthetic_tree_info
        if self.treemachine.use_v1:
            for key in ['draftTreeName', 'startNodeTaxName', 'startNodeID', 'startNodeOTTId']:
                self.assertTrue(key in cdict)
                tree_id = cdict['draftTreeName']
                node_id = str(cdict['startNodeID'])  # Odd that this is a string
                x = self.treemachine.get_synthetic_tree(tree_id,
                                                        format='newick',
                                                        node_id=node_id,
                                                        max_depth=2)
                self.assertEqual(x['treeID'], tree_id)
                self.assertTrue(x['newick'].startswith('('))
        else:
            tree_id, node_id = test_tol_about(self, cdict)
            # This now exceed the limit for tips in a tree, so expect HTTPError (400 Client Error: Bad Request)
            # instead of the previously expected ValueError
            self.assertRaises(HTTPError,
                              self.treemachine.get_synthetic_tree,
                              tree_id,
                              format='newick',
                              node_id=node_id)

    def testPrunedTree(self):
        if self.treemachine.use_v1:
            r = self.treemachine.get_synth_tree_pruned(ott_ids=example_ott_id_list)
            self.assertEqual(len(example_ott_id_list), len(r['found_nodes']))
        else:
            r = self.treemachine.induced_subtree(ott_ids=example_ott_id_list)
            for key in ['ott_ids_not_in_tree', u'node_ids_not_in_tree']:
                self.assertEqual(r[key], [])
        self.assertTrue(r['newick'].startswith('('))

    def testMRCA(self):
        if not self.treemachine.use_v1:
            r = self.treemachine.mrca(ott_ids=example_ott_id_list)
            self.assertTrue('mrca_node_id' in r)
            # print('node_info is', self.treemachine.node_info(r['mrca_node_id']))

    @unittest.skipIf(True, 'not sure whether this should be skipped...')
    def testSearchForTaxon(self):
        taxomachine = Taxomachine(self.domains)
        anolis_taxon = taxomachine.autocomplete('Anolis')
        ott_id = anolis_taxon[0]['ottId']
        node_id = self.treemachine.get_node_id_for_ott_id(ott_id)
        self.treemachine.get_synthetic_tree(format='newick', node_id=node_id, max_depth=12)


if __name__ == "__main__":
    unittest.main()
