#! /usr/bin/env python
import unittest
from peyotl.utility import get_logger
from peyotl.test.support import pathmap
from peyotl.nexson_syntax import can_convert_nexson_forms, \
                                 convert_nexson_format, \
                                 DIRECT_HONEY_BADGERFISH, \
                                 BADGER_FISH_NEXSON_VERSION, \
                                 PREFERRED_HONEY_BADGERFISH
from peyotl.struct_diff import DictDiff
_LOG = get_logger(__name__)

# round trip filename tuples
RT_TUPLES = [('otu.xml', 'otu.bf.json', 'otu-v1.0-nexson.json', 'otu-v1.2-nexson.json')]
    
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
        for t in RT_TUPLES:
            bf = t[1]
            hbf = t[2]
            obj = pathmap.nexson_obj(bf)
            h_expect = pathmap.nexson_obj(hbf)
            h = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            self._equal_blob_check(h, h_expect)

    def testConvertHBF1_0toBF(self):
        for t in RT_TUPLES:
            bf = t[1]
            hbf = t[2]
            obj = pathmap.nexson_obj(hbf)
            b_expect = pathmap.nexson_obj(bf)
            b = convert_nexson_format(obj, BADGER_FISH_NEXSON_VERSION)
            self._equal_blob_check(b, b_expect)

    def testConvertHBF1_2toHBF1_0(self):
        for t in RT_TUPLES:
            hbf = t[2]
            pbf = t[3]
            obj = pathmap.nexson_obj(pbf)
            h_expect = pathmap.nexson_obj(hbf)
            h = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            self._equal_blob_check(h, h_expect)

    def testConvertHBF1_0toHBF1_2(self):
        for t in RT_TUPLES:
            hbf = t[2]
            pbf = t[3]
            obj = pathmap.nexson_obj(hbf)
            b_expect = pathmap.nexson_obj(pbf)
            b = convert_nexson_format(obj, PREFERRED_HONEY_BADGERFISH)
            self._equal_blob_check(b_expect, b)
    def _equal_blob_check(self, first, second):
        if first != second:
            dd = DictDiff.create(first, second)
            er = dd.edits_expr()
            _LOG.info('\ndict diff: {d}'.format(d='\n'.join(er)))
            self.assertEqual(first, second)
if __name__ == "__main__":
    unittest.main()
