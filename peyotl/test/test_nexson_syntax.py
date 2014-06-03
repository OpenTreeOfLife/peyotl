#! /usr/bin/env python
from peyotl.nexson_syntax import can_convert_nexson_forms, \
                                 convert_nexson_format, \
                                 DIRECT_HONEY_BADGERFISH, \
                                 BADGER_FISH_NEXSON_VERSION, \
                                 BY_ID_HONEY_BADGERFISH, \
                                 PhyloSchema, \
                                 sort_meta_elements, \
                                 sort_arbitrarily_ordered_nexson
from peyotl.test.support import equal_blob_check
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)

# round trip filename tuples
RT_DIRS = ['otu', '9', ]

def _get_pair(par, f, s):
    bf = os.path.join(par, f)
    hbf = os.path.join(par, s)
    fp, sp = pathmap.nexson_source_path(bf), pathmap.nexson_source_path(hbf)
    if not os.path.exists(fp):
        _LOG.warn('\nTest skipped because {s} does not exist'.format(s=fp))
        return None, None
    if not os.path.exists(sp):
        _LOG.warn('\nTest skipped because {s} does not exist'.format(s=sp))
        return None, None
    return pathmap.nexson_obj(bf), pathmap.nexson_obj(hbf)

class TestPhyloSchema(unittest.TestCase):
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
    def testNexmlConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexml')
        nex = ps.serialize(o)
        self.assertTrue(nex.startswith('<'))

    def testNexusConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('nexus', content='tree', content_id='tree3')
        nex = ps.serialize(o)
        self.assertTrue(nex.startswith('#'))

    def testNewickConvViaPS(self):
        o = pathmap.nexson_obj('10/pg_10.json')
        ps = PhyloSchema('newick', content='tree', content_id='tree3')
        nex = ps.serialize(o)
        self.assertTrue(nex.startswith('('))

        """_format_list = ('newick', 'nexson', 'nexml', 'nexus')
    NEWICK, NEXSON, NEXML, NEXUS = range(4)
    _extension2format = {
        '.nexson' : 'nexson',
        '.nexml': 'nexml',
        '.nex': 'nex',
        '.tre': 'newick',
        '.nwk': 'newick',
    }
    _otu_label_list = ('ot:originallabel', 'ot:ottid', 'ot:otttaxonname')
    def __init__(self, **kwargs):
        '''Checks:
            'format',
            'type_ext', then 
            'output_nexml2json' (implicitly NexSON)
        '''
        if kwargs.get('format') is not None:
            self.format_str = kwargs['format'].lower()
        elif kwargs.get('type_ext') is not None:
            ext = kwargs['type_ext'].lower()
            try:
                self.format_str = PhyloSchema._extension2format[ext]
            except:
                raise ValueError('file extension "{}" not recognized'.format(kwargs['type_ext']))
        elif 'output_nexml2json' in kwargs:
            self.format_str = 'nexson'
            self.version = kwargs['output_nexml2json']
        else:
            raise ValueError('Expecting "format" or "type_ext" argument')
        try:
            self.format_code = PhyloSchema._format_list.index(self.format_str)
        except:
            raise ValueError('format "{}" not recognized'.format(self.format_str))
        if self.format_code == PhyloSchema.NEXSON
            try:
                if not hasattr(self, 'version'):
                    self.version = kwargs['version']
                if self.version == 'native':
                    self.version = kwargs['repo_nexml2json']
            except:
                raise ValueError('Expecting version of NexSON to be specified using "output_nexml2json" argument (or via some other mechanism)')
        else:
            self.otu_label = kwargs.get('tip_label', 'ot:originallabel').lower()
            if (self.otu_label not in PhyloSchema._otu_label_list) \
               and ('ot:{}'.format(self.otu_label) not in PhyloSchema._otu_label_list):
                m = '"tip_label" must be one of "{}"'.format('", "'.join(PhyloSchema._otu_label_list)
                    """


class TestConvert(unittest.TestCase):
    def testCanConvert(self):
        x = ["0.0.0", "1.0.0"]
        for i in x:
            for j in x:
                self.assertTrue(can_convert_nexson_forms(i, j))

    def testCannotConvert(self):
        x = ["0.0.0", "1.1.0"]
        for i in x:
            for j in x:
                if i == j:
                    continue
                self.assertFalse(can_convert_nexson_forms(i, j))

    def testConvertBFtoHBF1_0(self):
        for t in RT_DIRS:
            obj, b_expect = _get_pair(t, 'v0.0.json', 'v1.0.json')
            if obj is None:
                continue
            h = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            equal_blob_check(self, '', h, b_expect)

    def testConvertBFtoHBF1_2(self):
        for t in RT_DIRS:
            obj, b_expect = _get_pair(t, 'v0.0.json', 'v1.2.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, BY_ID_HONEY_BADGERFISH)
            equal_blob_check(self, '', b, b_expect)

    def testConvertHBF1_0toBF(self):
        for t in RT_DIRS:
            obj, b_expect = _get_pair(t, 'v1.0.json', 'v0.0.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, BADGER_FISH_NEXSON_VERSION)
            sort_meta_elements(b_expect)
            sort_meta_elements(b)
            equal_blob_check(self, '', b, b_expect)

    def testConvertHBF1_2toBF(self):
        for t in RT_DIRS:
            obj, b_expect = _get_pair(t, 'v1.2.json', 'v0.0.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, BADGER_FISH_NEXSON_VERSION)
            sort_arbitrarily_ordered_nexson(b_expect)
            sort_arbitrarily_ordered_nexson(b)
            equal_blob_check(self, '', b, b_expect)

    def testConvertHBF1_2toHBF1_0(self):
        for t in RT_DIRS:
            obj, b_expect = _get_pair(t, 'v1.2.json', 'v1.0.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            sort_arbitrarily_ordered_nexson(b_expect)
            sort_arbitrarily_ordered_nexson(b)
            equal_blob_check(self, '', b, b_expect)

    def testConvertHBF1_0toHBF1_2(self):
        for t in RT_DIRS:
            obj, b_expect = _get_pair(t, 'v1.0.json', 'v1.2.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, BY_ID_HONEY_BADGERFISH)
            equal_blob_check(self, '', b, b_expect)

if __name__ == "__main__":
    unittest.main()
