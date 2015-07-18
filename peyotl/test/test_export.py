#! /usr/bin/env python
from peyotl.nexson_syntax import extract_tree, PhyloSchema
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)

# round trip filename tuples
RT_DIRS = ['otu', '9', ]

class TestExtract(unittest.TestCase):

    def testNewickExport(self):
        n = pathmap.nexson_obj('10/pg_10.json')
        newick = extract_tree(n, 'tree3', PhyloSchema('newick', tip_label='ot:ottTaxonName', bracket_ingroup=True))
        self.assertTrue('[pre-ingroup-marker' in newick)
        self.assertTrue('[post-ingroup-marker' in newick)
        self.assertTrue(newick.startswith('('))
        self.assertTrue('*tip #1 not mapped' in newick)
        self.assertTrue('*tip #2 not mapped' in newick)
        self.assertTrue('*tip #3 not mapped' not in newick)
        newick = extract_tree(n, 'tree3', PhyloSchema('newick', tip_label='ot:ottTaxonName'))
        self.assertTrue('[pre-ingroup-marker' not in newick)
        self.assertTrue('[post-ingroup-marker' not in newick)
        self.assertTrue('*tip #1 not mapped' in newick)
        self.assertTrue('*tip #2 not mapped' in newick)
        self.assertTrue('*tip #3 not mapped' not in newick)
        self.assertTrue(newick.startswith('('))
        newick = extract_tree(n, 'tree3', PhyloSchema('newick', tip_label='ot:originallabel'))
        self.assertTrue('[pre-ingroup-marker' not in newick)
        self.assertTrue('[post-ingroup-marker' not in newick)
        self.assertTrue('*tip #' not in newick)

    def testTreeExport(self):
        n = pathmap.nexson_obj('10/pg_10.json')
        newick = extract_tree(n, 'tree3', PhyloSchema('nexus', tip_label='ot:ottTaxonName'))
        self.assertTrue(newick.startswith('#'))
    def testMimicPhylesystemExport(self):
        study_nexson = pathmap.nexson_obj('10/pg_10.json')
        src_schema = PhyloSchema('nexson', version='1.2.1')
        out_schema = PhyloSchema(schema='newick', content='tree', content_id='bogusID here')
        result_data = out_schema.convert(study_nexson, serialize=True, src_schema=src_schema)
        self.assertFalse(bool(result_data))
        out_schema = PhyloSchema(schema='nexus', content='tree', content_id='bogusID here')
        result_data = out_schema.convert(study_nexson, serialize=True, src_schema=src_schema)
        self.assertFalse(bool(result_data))
if __name__ == "__main__":
    unittest.main()
