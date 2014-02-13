#! /usr/bin/env python
import unittest
from peyotl.utility import get_logger
from peyotl.nexson_syntax import can_convert_nexson_forms
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

if __name__ == "__main__":
    unittest.main()
