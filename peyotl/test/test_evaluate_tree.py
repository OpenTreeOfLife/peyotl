#! /usr/bin/env python
"""
NOT IMPLEMENTED - test expected to fail, so removed...

from peyotl.evaluate_tree import evaluate_tree_rooting
from peyotl.ott import OTT
from peyotl.utility import get_config_setting, get_logger
from peyotl.nexson_proxy import NexsonProxy
from peyotl.test.support import pathmap
import unittest
_LOG = get_logger(__name__)
do_test = False
try:
    ott_dir = get_config_setting(section='ott', param='parent', default=False)
    if ott_dir is False or not ott_dir.endswith('/aster'):
        _LOG.debug('ott_dir setting is "{}" this does not look like it is the Asterales system'.format(ott_dir))
    else:
        do_test = True
except:
    _LOG.debug('[ott]/parent setting could not be read correctly.')
@unittest.skipIf(not do_test, 'the test_evaluate_tree.py is experimental, and currently skipped. You can only run if you have your OTT/parent configuration set' \
                              ' to point to a directory called "aster" (which should hold the taxonomy of Asterales) ' \
                              'See http://opentreeoflife.github.io/peyotl/configuration/ ' \
                              ' and open tree of life reference taxonomy documentation about the Asterales test system')
class TestProxy(unittest.TestCase):
    def setUp(self):
        self.nexson = pathmap.nexson_obj('pg_329/pg_329.json')
        self.np = NexsonProxy(nexson=self.nexson)
    def testTaxoRooting(self):
        ott = OTT()
        phylo = self.np.get_tree(tree_id='tree324')
        evaluate_tree_rooting(self.nexson, ott, phylo)

if __name__ == "__main__":
    unittest.main()
"""