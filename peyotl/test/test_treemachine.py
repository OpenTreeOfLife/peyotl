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
    def testSearchForTaxon(self):
        taxomachine = Taxomachine(self.domains)
        anolis_taxon = taxomachine.TNRS('Anolis')
        ottId = anolis_taxon[0]['ottId']
        node_id = self.treemachine.get_node_id_for_ott_id(ottId)
        x = self.treemachine.get_synthetic_tree(format='newick', node_id=node_id, max_depth=12)
        #print '{};'.format(x['newick'])

    def testSynthTree(self):
        cdict = self.treemachine.get_synthetic_tree_info()
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
    def testSourceTree(self):
        source_id_list = self.treemachine.get_synthetic_tree_id_list()
        self.assertTrue(isinstance(source_id_list, list))
        f = source_id_list[0]
        r = self.treemachine.get_source_tree(f)
        self.assertEqual(r['treeID'], f)
        self.assertTrue(r['newick'].startswith('('))
if __name__ == "__main__":
    unittest.main()
