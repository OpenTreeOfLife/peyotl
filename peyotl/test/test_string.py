#! /usr/bin/env python
from peyotl.string import build_taxonomic_regex, \
                          find_intervening_fragments, \
                          create_library_of_intervening_fragments
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)

@unittest.skip('string splitting not working, yet...')
class TestString(unittest.TestCase):
    def testBuildTaxReg(self):
        r = build_taxonomic_regex([('blah Homo_sapiens+515', 'Homo sapiens'),
                                                     ('blahhumbug Homo_sapiens+516', 'Homo sapiens')])
        print r[0].pattern
        self.assertEqual(len(r), 1)
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
    def testCreateLibraryInterveningFragments(self):
        r = create_library_of_intervening_fragments([('blah Homo_sapiens+515', 'Homo sapiens'),
                                                     ('blahhumbug Homo_sapiens+516', 'Homo sapiens')])
        self.assertEqual(len(r), 3)
        self.assertEqual(len(r[2]), 2)
        self.assertEqual(r[2][0], [['blah ', 'Homo', '_', 'sapiens', '+515']])
        self.assertEqual(r[2][1], [['blahhumbug ', 'Homo', '_', 'sapiens','+516']])
if __name__ == "__main__":
    unittest.main(verbosity=5)
