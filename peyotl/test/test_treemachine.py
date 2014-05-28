#! /usr/bin/env python
from peyotl.api import Treemachine, Taxomachine
from peyotl.test.support.pathmap import get_test_ot_service_domains
from peyotl.utility import get_logger
import unittest

_LOG = get_logger(__name__)

class TestTreemachine(unittest.TestCase):
    def setUp(self):
        self.domains = get_test_ot_service_domains()
        self.treemachine = Treemachine(self.domains)
    def testSynthTree(self):
        cdict = self.treemachine.getSyntheticTreeInfo()
        for key in ['draftTreeName', 'startNodeTaxName', 'startNodeID', 'startNodeOTTId']:
            self.assertTrue(key in cdict)
        treeID = cdict['draftTreeName']
        nodeID = str(cdict['startNodeID']) # Odd that this is a string
        x = self.treemachine.getSyntheticTree(treeID,
                                              format='newick',
                                              nodeID=nodeID,
                                              maxDepth=2)
        self.assertEqual(x['treeID'], treeID)
        self.assertTrue(x['newick'].startswith('('))
    def testSourceTree(self):
        source_id_list = self.treemachine.getSourceTreesIDList()
        self.assertTrue(isinstance(source_id_list, list))
        f = source_id_list[0]
        r = self.treemachine.getSourceTree(f)
        self.assertEqual(r['treeID'], f)
        self.assertTrue(r['newick'].startswith('('))
    def testSearchForTaxon(self):
        taxomachine = Taxomachine(self.domains)

if __name__ == "__main__":
    unittest.main()
