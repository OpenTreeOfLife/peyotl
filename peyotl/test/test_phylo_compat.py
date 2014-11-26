#! /usr/bin/env python
from peyotl.phylo.compat import SplitComparison, sets_are_rooted_compat, compare_sets_as_splits
from peyotl.utility import get_logger
import unittest
_LOG = get_logger(__name__)
class TestCompat(unittest.TestCase):
    def testRootedCompat(self):
        self.assertTrue(sets_are_rooted_compat(set([1, 2]), set([1, 2, 3])))
        self.assertTrue(sets_are_rooted_compat(set([1, 2, 3]), set([1, 2, 3])))
        self.assertTrue(sets_are_rooted_compat(set([1, 2, 3]), set([1, 2])))
        self.assertTrue(sets_are_rooted_compat(set([1, 2, 3]), set([4, 92])))
        self.assertFalse(sets_are_rooted_compat(set([1, 2, 4]), set([4, 92])))
    def testCompareSetsAsSplits(self):
        uni = frozenset([1, 2, 3, 4, 92])
        self.assertEqual(compare_sets_as_splits(set([1, 2, 4]), set([4, 92]), uni), SplitComparison.UNROOTED_INCOMPATIBLE)
        self.assertEqual(compare_sets_as_splits(set([1, 2, 4]), set([1, 2, 3]), uni), SplitComparison.UNROOTED_INCOMPATIBLE)
        self.assertEqual(compare_sets_as_splits(set([1, 2, 4]), set([1, 2, 4]), uni), SplitComparison.ROOTED_EQUIVALENT)
        self.assertEqual(compare_sets_as_splits(set([1, 2, 4]), set([3, 92]), uni), SplitComparison.UNROOTED_EQUIVALENT)
        self.assertEqual(compare_sets_as_splits(set([1, 2, 4]), set([4, 3, 92]), uni), SplitComparison.UNROOTED_COMPAT)
        self.assertEqual(compare_sets_as_splits(set([1, 2, 4]), set([2, 1]), uni), SplitComparison.ROOTED_COMPAT)
if __name__ == "__main__":
    unittest.main()
