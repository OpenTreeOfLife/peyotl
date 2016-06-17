#!/usr/bin/env python
'''Takes meta properties for a tree requested'''
from __future__ import absolute_import, division, print_function, unicode_literals
from peyotl.api import PhylesystemAPI
from peyotl.utility import propinquity_fn_to_study_tree
import codecs
import sys

out = codecs.getwriter('utf-8')(sys.stdout)

NON_META = frozenset([u'^ot:rootNodeId',
                      u'nodeById',
                      u'edgeBySourceId',
                      u'^ot:inGroupClade',
                      u'@xsi:type',
                      u'^ot:branchLengthTimeUnit',
                      u'^ot:branchLengthDescription',
                      u'^ot:tag',
                      u'^ot:branchLengthMode'])
for arg in sys.argv[1:]:
    study_id, tree_id = propinquity_fn_to_study_tree(arg, strip_extension=False)
    pa = PhylesystemAPI(get_from='local')
    try:
        tree = pa.get(study_id, tree_id=tree_id)[tree_id]
        print('Tree "{}" in study "{}":'.format(tree_id, study_id))
        for k, v in tree.items():
            if (v is not None) and (v is not '') and (k not in NON_META):
                print(k, v)
    except:
        sys.stderr.write('WARNING: did not find tree "{}" in study "{}"'.format(tree_id, study_id))
