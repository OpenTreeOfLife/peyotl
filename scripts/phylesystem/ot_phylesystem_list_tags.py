#!/usr/bin/env python
'''Examines the tags (ot:tag) study. Prints out a list 
of each unique tag used in the studies '''
tax_prop_name = '^ot:ottTaxonName'
orig_prop_name = '^ot:originalLabel'
label_prop_name = '@label'
from peyotl import gen_otu_dict, iter_node
from peyotl.manip import iter_trees
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.nexson_syntax import get_nexml_el
from collections import defaultdict
import codecs
import sys

phy = Phylesystem()
study_dict = defaultdict(int)
tree_dict = defaultdict(int)
out = codecs.getwriter('utf-8')(sys.stdout)
for study_id, n in phy.iter_study_objs():
    nexml = get_nexml_el(n)
    t = nexml.get('^ot:tag')
    if t:
        #print study_id, t
        if isinstance(t, list):
            for tag in t:
                study_dict[tag] += 1
        else:
            study_dict[t] += 1
    for trees_group_id, tree_id, tree in iter_trees(n):
        t = tree.get('^ot:tag')
        if t:
            #print study_id, tree_id, t
            if isinstance(t, list):
                for tag in t:
                    study_dict[tag] += 1
            else:
                tree_dict[t] += 1
print '\nStudy tag counts:'
for k,v in study_dict.items():
    print k,'\t',v
print '\nTree tag counts:'
for k,v in tree_dict.items():
    print k,'\t',v

