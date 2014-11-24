#! /usr/bin/env python
from peyotl.utility.tokenizer import NewickTokenizer, NewickTokenType
from peyotl.utility.str_util import StringIO
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)
class TestNewickTokenizer(unittest.TestCase):
    def testSimple(self):
        exp = ['(', '(', 'h', ',', 'p', ')', 'hp', ',', 'g', ')', 'hpg', ';']
        self._do_test('((h,p)hp,g)hpg;', exp)
        self._do_test('((h,p[test])hp,g)hpg;', exp)
        self._do_test('  ( (  h , p[test] [test2])  hp,  g) hpg ;', exp)
    def _do_test(self, content, expected):
        self.assertEqual([i for i in NewickTokenizer(StringIO(content))], expected)

if __name__ == "__main__":
    unittest.main()
