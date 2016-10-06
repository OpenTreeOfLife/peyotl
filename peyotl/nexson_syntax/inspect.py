#!/usr/bin/env python
"""Simple inspection of NexSON blob
 Functions here should:
    - work on any nexson version that peyotl supports and,
    - avoid any coercion of the NexSON to another version.
(unlike the functions in peyotl.manip, which may change the NexSON version)
"""
from __future__ import absolute_import, print_function, division
from peyotl.nexson_syntax import detect_nexson_version, get_nexml_el, _is_by_id_hbf
from peyotl.utility import get_logger

_LOG = get_logger(__name__)


def count_num_trees(nexson, nexson_version=None):
    """Returns the number of trees summed across all tree
    groups.
    """
    if nexson_version is None:
        nexson_version = detect_nexson_version(nexson)
    nex = get_nexml_el(nexson)
    num_trees_by_group = []
    if _is_by_id_hbf(nexson_version):
        for tree_group in nex.get('treesById', {}).values():
            nt = len(tree_group.get('treeById', {}))
            num_trees_by_group.append(nt)
    else:
        trees_group = nex.get('trees', [])
        if isinstance(trees_group, dict):
            trees_group = [trees_group]
        for tree_group in trees_group:
            t = tree_group.get('tree')
            if isinstance(t, list):
                nt = len(t)
            else:
                nt = 1
            num_trees_by_group.append(nt)
    return sum(num_trees_by_group)
