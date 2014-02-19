#! /usr/bin/env python
from peyotl.nexson_syntax import can_convert_nexson_forms, \
                                 convert_nexson_format, \
                                 DIRECT_HONEY_BADGERFISH, \
                                 BADGER_FISH_NEXSON_VERSION, \
                                 PREFERRED_HONEY_BADGERFISH, \
                                 sort_meta_elements, \
                                 write_as_json
from peyotl.struct_diff import DictDiff
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)

# round trip filename tuples
RT_DIRS = ['9', 'otu',]

class TestConvert(unittest.TestCase):
    def _equal_blob_check(self, first, second):
        if first != second:
            dd = DictDiff.create(first, second)
            write_as_json(first, '.obtained_rt')
            write_as_json(second, '.expected_rt')
            er = dd.edits_expr()
            _LOG.info('\ndict diff: {d}'.format(d='\n'.join(er)))
            if first != second:
                self.assertEqual("", "Roundtrip failed see files .obtained_rt and .expected_rt")
    def _get_pair(self, par, f, s):
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
            obj, b_expect = self._get_pair(t, 'v0.0.json', 'v1.0.json')
            if obj is None:
                continue
            h = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            self._equal_blob_check(h, b_expect)

    def testConvertBFtoHBF1_2(self):
        for t in RT_DIRS:
            obj, b_expect = self._get_pair(t, 'v0.0.json', 'v1.2.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, PREFERRED_HONEY_BADGERFISH)
            self._equal_blob_check(b, b_expect)

    def testConvertHBF1_0toBF(self):
        for t in RT_DIRS:
            obj, b_expect = self._get_pair(t, 'v1.0.json', 'v0.0.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, BADGER_FISH_NEXSON_VERSION)
            sort_meta_elements(b_expect)
            sort_meta_elements(b)
            self._equal_blob_check(b, b_expect)

    def testConvertHBF1_2toBF(self):
        for t in RT_DIRS:
            obj, b_expect = self._get_pair(t, 'v1.2.json', 'v0.0.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, BADGER_FISH_NEXSON_VERSION)
            sort_meta_elements(b_expect)
            sort_meta_elements(b)
            self._equal_blob_check(b, b_expect)

    def testConvertHBF1_2toHBF1_0(self):
        for t in RT_DIRS:
            obj, b_expect = self._get_pair(t, 'v1.2.json', 'v1.0.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
            self._equal_blob_check(b, b_expect)

    def testConvertHBF1_0toHBF1_2(self):
        for t in RT_DIRS:
            obj, b_expect = self._get_pair(t, 'v1.0.json', 'v1.2.json')
            if obj is None:
                continue
            b = convert_nexson_format(obj, PREFERRED_HONEY_BADGERFISH)
            self._equal_blob_check(b, b_expect)

if __name__ == "__main__":
    unittest.main()
