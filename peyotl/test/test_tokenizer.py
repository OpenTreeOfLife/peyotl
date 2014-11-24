#! /usr/bin/env python
from peyotl.utility.tokenizer import NewickTokenizer, NewickTokenType
from peyotl.utility.str_util import StringIO
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)
class TestNewickTokenizer(unittest.TestCase):
    def testSimple(self):
        print([i for i in NewickTokenizer(StringIO('((h,p)hp,g)hpg;'))])

if __name__ == "__main__":
    unittest.main()
