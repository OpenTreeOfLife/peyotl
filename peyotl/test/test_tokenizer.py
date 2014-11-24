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
    def testQuoted(self):
        exp = ['(', '(', 'h ', ',', 'p', ')', 'h p', ',', "g()[],':_", ')', 'hpg', ';']
        self._do_test("((h_ ,'p')h p,'g()[],'':_')hpg;", exp)
        self._do_test("(('h ',p)h p,'g()[],'':_')hpg;", exp)
    def _do_test(self, content, expected):
        self.assertEqual([i for i in NewickTokenizer(StringIO(content))], expected)
    def testOddQuotes(self):
        content = "((h_ ,'p)h p,g()[],:_)hpg;"
        tok = NewickTokenizer(StringIO(content))
        content = "((h_ ,'p')h p,'g()[]',:_')hpg;"
        tok = NewickTokenizer(StringIO(content))
        self.assertRaises(Exception, tok.tokens)
    def testBranchLen(self):
        exp = ['(', '(', 'h', ':', '4.0', ',', 'p', ':', '1.1461E-5', ')', 'hp', ':', '1351.146436', ',', 'g', ')', 'hpg', ';']
        self._do_test('((h:4.0,p:1.1461E-5)hp:1351.146436,g)hpg;', exp)

if __name__ == "__main__":
    unittest.main()
