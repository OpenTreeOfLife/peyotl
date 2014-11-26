#!/usr/bin/env python
from enum import Enum
class UnrootedConflictStatus(Enum):
    EQUIVALENT = 0
    INCOMPATIBLE = 1
    RESOLVES = 2 # compatible with "other" tree, and split is not in that tree
    TRIVIAL = 3 # will be compatible with any taxonomy
    NOT_COMPARABLE = 4 # e.g. lacking an OTT ID in a comparison to taxonomy

class SplitComparison(Enum):
    UNROOTED_INCOMPATIBLE = 0x00 # will conflict on any rooting
                                 # 1 bit is the "unrooted compat" bit
                                 # 2 bit is the "rooted compat" bit
                                 # 4 is the "unroot equiv bit"
                                 # 8 is the "root equiv bit"
    UNROOTED_COMPAT = 0x01 # both could fit on the same rooted tree if one were flipped
    ROOTED_COMPAT = 0x03 # both could fit on the same rooted tree (without altering)
    UNROOTED_EQUIVALENT = 0x07 # rooted differently, but compatible in an unrooted sense
    ROOTED_EQUIVALENT = 0x0F # represent the same partitioning of leaves

def sets_are_rooted_compat(one_set, other):
    '''treats the 2 sets are sets of taxon IDs on the same (unstated)
    universe of taxon ids.
    Returns True clades implied by each are compatible and False otherwise
    '''
    if one_set.issubset(other) or other.issubset(one_set):
        return True
    inter = one_set.intersection(other)
    return not bool(inter)

def compare_sets_as_splits(one_set, other, el_universe):
    if one_set.issubset(other) or other.issubset(one_set):
        if one_set == other:
            return SplitComparison.ROOTED_EQUIVALENT
        return SplitComparison.ROOTED_COMPAT
    inter = one_set.intersection(other)
    if not bool(inter):
        if len(one_set) + len(other) == len(el_universe):
            return SplitComparison.UNROOTED_EQUIVALENT
        return SplitComparison.UNROOTED_COMPAT
    if len(one_set) + len(other) - len(inter) == len(el_universe):
        return SplitComparison.UNROOTED_COMPAT
    return SplitComparison.UNROOTED_INCOMPATIBLE

