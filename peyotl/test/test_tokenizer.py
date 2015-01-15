#! /usr/bin/env python
from peyotl.utility.tokenizer import NewickTokenizer, NewickEvents, NewickEventFactory
from peyotl.utility.str_util import StringIO
from peyotl.utility import get_logger
import unittest
from copy import deepcopy
_LOG = get_logger(__name__)
class TestNewickTokenizer(unittest.TestCase):
    def testSimple(self):
        exp = ['(', '(', 'h', ',', 'p', ')', 'hp', ',', 'g', ')', 'hpg', ';']
        content = '((h,p)hp,g)hpg;'
        self._do_test(content, exp)
        content = '((h,p[test])hp,g)hpg;'
        self._do_test(content, exp)
        content = '  ( (  h , p[test] [test2])  hp,  g) hpg ;'
        self._do_test(content, exp)
    def testQuoted(self):
        exp = ['(', '(', 'h ', ',', 'p', ')', 'h p', ',', "g()[],':_", ')', 'hpg', ';']
        content = "((h_ ,'p')h p,'g()[],'':_')hpg;"
        self._do_test(content, exp)
        content = "(('h ',p)h p,'g()[],'':_')hpg;"
        self._do_test(content, exp)
    def _do_test(self, content, expected):
        self.assertEqual([i for i in NewickTokenizer(StringIO(content))], expected)
    def testOddQuotes(self):
        content = "((h_ ,'p)h p,g()[],:_)hpg;"
        tok = NewickTokenizer(StringIO(content))
        content = "((h_ ,'p')h p,'g()[]',:_')hpg;"
        tok = NewickTokenizer(StringIO(content))
        self.assertRaises(Exception, tok.tokens)
    def testBranchLen(self):
        exp = ['(', '(', 'h', ':', '4.0', ',', 'p', ':', '1.1461E-5', ')',
               'hp', ':', '1351.146436', ',', 'g', ')', 'hpg', ';']
        content = '((h:4.0,p:1.1461E-5)hp:1351.146436,g)hpg;'
        self._do_test(content, exp)

class TestNewickEvents(unittest.TestCase):
    def testSimple(self):
        exp = [{'type': NewickEvents.OPEN_SUBTREE, 'comments': []},
               {'type': NewickEvents.OPEN_SUBTREE, 'comments': []},
               {'edge_info': None, 'type': NewickEvents.TIP, 'comments': [], 'label': 'h'},
               {'edge_info': None, 'type': NewickEvents.TIP, 'comments': [], 'label': 'p'},
               {'edge_info': None, 'type': NewickEvents.CLOSE_SUBTREE, 'comments': [], 'label': 'hp'},
               {'edge_info': None, 'type': NewickEvents.TIP, 'comments': [], 'label': 'g'},
               {'edge_info': None, 'type': NewickEvents.CLOSE_SUBTREE, 'comments': [], 'label': 'hpg'}
              ]
        content = '((h,p)hp,g)hpg;'
        self._do_test(content, exp)
        content = '((h,[pretest]p[test][posttest])hp,g)hpg;'
        exp = [{'type': NewickEvents.OPEN_SUBTREE, 'comments': []},
               {'type': NewickEvents.OPEN_SUBTREE, 'comments': []},
               {'edge_info': None, 'type': NewickEvents.TIP, 'comments': [], 'label': 'h'},
               {'edge_info': None, 'type': NewickEvents.TIP, 'comments': ['pretest', 'test', 'posttest'], 'label': 'p'},
               {'edge_info': None, 'type': NewickEvents.CLOSE_SUBTREE, 'comments': [], 'label': 'hp'},
               {'edge_info': None, 'type': NewickEvents.TIP, 'comments': [], 'label': 'g'},
               {'edge_info': None, 'type': NewickEvents.CLOSE_SUBTREE, 'comments': [], 'label': 'hpg'}
              ]
        self._do_test(content, exp)
    def _do_test(self, content, expected):
        e = [deepcopy(i) for i in NewickEventFactory(tokenizer=NewickTokenizer(stream=StringIO(content)))]
        #print(e)
        self.assertEqual(e, expected)

if __name__ == "__main__":
    unittest.main()
