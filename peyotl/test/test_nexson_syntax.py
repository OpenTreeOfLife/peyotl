#! /usr/bin/env python
import unittest
from peyotl.utility import get_logger
from peyotl.test.support import pathmap
from peyotl.nexson_syntax import can_convert_nexson_forms, \
                                 convert_nexson_format, \
                                 DIRECT_HONEY_BADGERFISH, \
                                 BADGER_FISH_NEXSON_VERSION

_LOG = get_logger(__name__)

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

    def testConvertBFtoHBF1_1(self):
        obj = pathmap.nexson_obj('otu.bf.json')
        h_expect = pathmap.nexson_obj('otu-v1.0-nexson.json')
        h = convert_nexson_format(obj, DIRECT_HONEY_BADGERFISH)
        self.assertEqual(h, h_expect)
if __name__ == "__main__":
    unittest.main()
