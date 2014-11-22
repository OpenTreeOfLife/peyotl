#! /usr/bin/env python
from peyotl.phylo.tree import TreeWithPathsInEdges
from peyotl.utility import get_logger
import unittest
_bogus_id2par = {'h': 'hp',
                 'p': 'hp',
                 'g': 'hpg',
                 'hp': 'hpg',
                 'hpg': 'hpgPo',
                 'Po': 'hpgPo',
                 'Hy': 'HySi',
                 'Si': 'HySi',
                 'HySi': 'hpgPoHySi',
                 'hpgPo': 'hpgPoHySi',
                 'bogus_tip': 'bogus_internal',
                 'bogus_internal': 'bogus_i2',
                 'bogus_i3': 'bogus_i4',
                 'bogus_i4': 'bogus_i5',
                 'bogus_i5': 'bogus_i6',
                 'bogus_i6': 'bogus_root', }
_LOG = get_logger(__name__)
class TestPhyloTree(unittest.TestCase):
    pass

if __name__ == "__main__":
    unittest.main()
