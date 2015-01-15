#!/usr/bin/env python
'''Examines each otu in each study. Prints out any
case in which the otu label is not the ot:originalLabel or
the ot:ottTaxonName'''
tax_prop_name = '^ot:ottTaxonName'
orig_prop_name = '^ot:originalLabel'
label_prop_name = '@label'
from peyotl import gen_otu_dict, iter_node
from peyotl.manip import iter_trees
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.nexson_syntax import get_nexml_el
import codecs
import sys
phy = Phylesystem()
study_tags = set()
tree_tags = set()
out = codecs.getwriter('utf-8')(sys.stdout)
for study_id, n in phy.iter_study_objs():
    nexml = get_nexml_el(n)
    t = nexml.get('^ot:tag')
    if t:
        print study_id, t
        if isinstance(t, list):
            study_tags.update(t)
        else:
            study_tags.add(t)
    for trees_group_id, tree_id, tree in iter_trees(n):
        t = tree.get('^ot:tag')
        if t:
            print study_id, tree_id, t
            if isinstance(t, list):
                tree_tags.update(t)
            else:
                tree_tags.add(t)
print 'study tags:\n    ', '\n    '.join(study_tags)
print 'tree tags:\n    ', '\n    '.join(tree_tags)