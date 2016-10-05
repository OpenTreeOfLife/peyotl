#! /usr/bin/env python
import sys
import unittest

from peyotl import write_as_json
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.test.support import pathmap


class TestPhylesystem(unittest.TestCase):
    def testCachedValidation(self):
        try:
            # noinspection PyPackageRequirements
            import dogpile.cache
        except:
            pass
        else:
            r = pathmap.get_test_repos()
            p = Phylesystem(r)
            nexson, sha = p.return_study('xy_10')
            r = p.add_validation_annotation(nexson, sha)
            cache_hits = p._cache_hits
            r1 = p.add_validation_annotation(nexson, sha)
            self.assertEqual(1 + cache_hits, p._cache_hits)
            self.assertEqual(r, r1)
            write_as_json(nexson, sys.stdout)


if __name__ == "__main__":
    unittest.main()
