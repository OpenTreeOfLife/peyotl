#! /usr/bin/env python
from peyotl.nexson_syntax import PhyloSchema
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)
#pylint does not realize that serialize returns a string, so generates lots of
#   spurious errors
#pylint: disable=E1103
# round trip filename tuples
RT_DIRS = ['otu', '9', ]


class TestPhyloSchema(unittest.TestCase):
    def testUrlGen(self):
        _prefix = 'http://devapi.opentreeoflife.org/v2'
        url, params = PhyloSchema(type_ext='.nexml', otu_label='otttaxonname').phylesystem_api_url(_prefix, 'pg_719')
        self.assertEqual('{}/study/pg_719.nexml'.format(_prefix), url)
        self.assertEqual({'otu_label': 'ot:otttaxonname'}, params)
        url, params = PhyloSchema(type_ext='.nexml').phylesystem_api_url(_prefix, 'pg_719')
        self.assertEqual('{}/study/pg_719.nexml'.format(_prefix), url)
        self.assertEqual({}, params)

class Skip(object):
    def testNexmlConvByExtViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema(type_ext='.nexml', otu_label='otttaxonname')
        nex = ps.serialize(o, src_schema=PhyloSchema('nexson', version='1.2.1'))
        self.assertTrue(nex.startswith('<')) #pylint: disable=E1103
    def testPS(self):
        self.assertRaises(ValueError, PhyloSchema, schema='bogus')
        self.assertRaises(ValueError, PhyloSchema, content='bogus')
        self.assertRaises(ValueError, PhyloSchema)
        PhyloSchema('nexson', output_nexml2json='1.2')
        self.assertRaises(ValueError, PhyloSchema, schema='nexson')
        self.assertRaises(ValueError, PhyloSchema, schema='nexson', version='1.3')
        self.assertRaises(ValueError, PhyloSchema, schema='newick', tip_label='bogus')
        self.assertRaises(ValueError, PhyloSchema, schema='nexus', tip_label='bogus')
        self.assertRaises(ValueError, PhyloSchema, schema='nexml', tip_label='bogus')

    def testSubTreesConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('newick',
                         content='subtree',
                         content_id=('tree3', 'node508'),
                         version='1.2.1')
        x = ps.serialize(o)
        self.assertTrue(x.startswith('(')) #pylint: disable=E1103
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('newick',
                         content='subtree',
                         content_id=('tree3', 'ingroup'),
                         version='1.2.1')
        x = ps.serialize(o)
        self.assertTrue(x.startswith('(')) #pylint: disable=E1103
    def testTreesConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexson', content='tree', content_id='tree3', version='1.2.1')
        x = ps.serialize(o)
        self.assertTrue(x.startswith('{')) #pylint: disable=E1103
    def testMetaConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexson', content='meta', version='1.2.1')
        x = ps.serialize(o)
        self.assertTrue(x.startswith('{')) #pylint: disable=E1103
    def testOtusConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexson', content='otus', version='1.2.1')
        x = ps.serialize(o)
        self.assertTrue(x.startswith('{')) #pylint: disable=E1103
    def testOtuConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexson', content='otu', content_id='otu190', version='1.2.1')
        x = ps.serialize(o)
        self.assertTrue(x.startswith('{')) #pylint: disable=E1103
    def testOtuMapConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexson', content='otumap', version='1.2.1')
        x = ps.serialize(o)
        self.assertTrue(x.startswith('{')) #pylint: disable=E1103
    def testNexmlConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexml')
        nex = ps.serialize(o)
        self.assertTrue(nex.startswith('<')) #pylint: disable=E1103

    def testNexusConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexus', content='tree', content_id='tree3')
        nex = ps.convert(o, serialize=True)
        self.assertTrue(nex.startswith('#')) #pylint: disable=E1103

    def testNexusConvStudyViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema(type_ext='.nex')
        nex = ps.convert(o, serialize=True)
        self.assertTrue(nex.startswith('#')) #pylint: disable=E1103

    def testNewickConvStudyViaPS(self):
        o = pathmap.nexson_obj('9/v1.2.json')
        ps = PhyloSchema(type_ext='.tre')
        nex = ps.convert(o, serialize=True)
        self.assertTrue(nex.startswith('(')) #pylint: disable=E1103

    def testNexusConvByExtViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema(None, type_ext='.nex', content='tree', content_id='tree3')
        nex = ps.serialize(o)
        self.assertTrue(nex.startswith('#')) #pylint: disable=E1103

    def testNewickConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('newick', content='tree', content_id='tree3')
        nex = ps.serialize(o)
        self.assertTrue(nex.startswith('(')) #pylint: disable=E1103

if __name__ == "__main__":
    unittest.main()

