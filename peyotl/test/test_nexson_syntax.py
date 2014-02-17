#! /usr/bin/env python
from peyotl.nexson_syntax import can_convert_nexson_forms, \
                                 convert_nexson_format, \
                                 DIRECT_HONEY_BADGERFISH, \
                                 BADGER_FISH_NEXSON_VERSION, \
                                 PREFERRED_HONEY_BADGERFISH,  \
                                 write_as_json
from peyotl.struct_diff import DictDiff
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)

# round trip filename tuples
if False:
    RT_DIRS = ['simple-phenoscape'] #phenoscape', 'otu']
else:
    RT_DIRS = ['otu',]

class TestConvert(unittest.TestCase):
    def _equal_blob_check(self, first, second):
        if first != second:
            dd = DictDiff.create(first, second)
            write_as_json(first, '.first_arg_equal_blob_check')
            write_as_json(second, '.second_arg_equal_blob_check')
            er = dd.edits_expr()
            _LOG.info('\ndict diff: {d}'.format(d='\n'.join(er)))
            self.assertEqual(first, second)

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
            bf = os.path.join(t, 'v0.0.json')
            hbf = os.path.join(t, 'v1.0.json')
            obj = pathmap.nexson_obj(bf)
            h_expect = pathmap.nexson_obj(hbf)
            h = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            self._equal_blob_check(h, h_expect)

    def testConvertHBF1_0toBF(self):
        for t in RT_DIRS:
            bf = os.path.join(t, 'v0.0.json')
            hbf = os.path.join(t, 'v1.0.json')
            obj = pathmap.nexson_obj(hbf)
            b_expect = pathmap.nexson_obj(bf)
            b = convert_nexson_format(obj, BADGER_FISH_NEXSON_VERSION)
            self._equal_blob_check(b, b_expect)

    def testConvertHBF1_2toHBF1_0(self):
        for t in RT_DIRS:
            hbf = os.path.join(t, 'v1.0.json')
            pbf = os.path.join(t, 'v1.2.json')
            obj = pathmap.nexson_obj(pbf)
            h_expect = pathmap.nexson_obj(hbf)
            h = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            self._equal_blob_check(h, h_expect)

    def testConvertHBF1_0toHBF1_2(self):
        for t in RT_DIRS:
            hbf = os.path.join(t, 'v1.0.json')
            pbf = os.path.join(t, 'v1.2.json')
            obj = pathmap.nexson_obj(hbf)
            b_expect = pathmap.nexson_obj(pbf)
            b = convert_nexson_format(obj, PREFERRED_HONEY_BADGERFISH)
            self._equal_blob_check(b_expect, b)


if __name__ == "__main__":
    unittest.main()
