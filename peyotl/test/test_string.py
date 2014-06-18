#! /usr/bin/env python
from peyotl.string import find_intervening_fragments
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)

class TestString(unittest.TestCase):
    def testSimplestIntervening(self):
        f_list = find_intervening_fragments('short', ['long'])
        self.assertEqual(f_list, None)
        f_list = find_intervening_fragments('short', ['short'])
        self.assertEqual(f_list, [['', '']])
        f_list = find_intervening_fragments('ashortb', ['short'])
        self.assertEqual(f_list, [['a', 'b']])
    def testIntervening(self):
        f_list = find_intervening_fragments('abcde', ['b', 'd'])
        self.assertEqual(len(f_list), 1)
        self.assertEqual(f_list[0], ['a', 'c', 'e'])
    def testRepIntervening(self):
        f_list = find_intervening_fragments('abcbedf', ['b', 'd'])
        self.assertEqual(len(f_list), 2)
        self.assertEqual(f_list[0], ['a', 'cbe', 'f'])
        self.assertEqual(f_list[1], ['abc', 'e', 'f'])
if __name__ == "__main__":
    unittest.main(verbosity=5)
