#! /usr/bin/env python
from peyotl.nexson_syntax import extract_tree, PhyloSchema
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)

# round trip filename tuples
RT_DIRS = ['otu', '9', ]

def _get_pair(par, f, s):
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

class TestExtract(unittest.TestCase):

    def testTreeExport(self):
        n = pathmap.nexson_obj('10/pg_10.json')
        newick = extract_tree(n, 'tree3', PhyloSchema('nexus', tip_label='ot:ottTaxonName'))
        self.assertTrue(newick.startswith('#'))

if __name__ == "__main__":
    unittest.main()
