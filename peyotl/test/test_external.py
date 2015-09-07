#! /usr/bin/env python
from peyotl.external import get_ot_study_info_from_treebase_nexml
from peyotl import write_as_json
from peyotl.utility import get_logger
import unittest
import codecs
_LOG = get_logger(__name__)

class TestExternal(unittest.TestCase):
    pass
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with codecs.open(sys.argv[1], 'r', encoding='utf-8') as inp:
            content = inp.read()
        b = get_ot_study_info_from_treebase_nexml(nexml_content=content)
        write_as_json(b, sys.stdout)
    #unittest.main()
