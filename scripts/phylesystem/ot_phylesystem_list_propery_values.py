#!/usr/bin/env python
'''For every study that has the study-level property name 
which is passed in as a command line argument, the script prints out
the study ID and the property value.

For example:
    ot_phylesystem_list_study_property.py '^ot:studyPublication'

prints out the study's URL for each study that has this property set.
'''
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.nexson_syntax import get_nexml_el
from peyotl.manip import iter_trees
from collections import defaultdict
import argparse
import codecs
import sys
import os
description = __doc__
prog = os.path.split(sys.argv[0])[-1]
parser = argparse.ArgumentParser(prog=prog, description=description)
parser.add_argument('--set', action='store_true', default=False, required=False, help="report the set of values")
parser.add_argument('--tree', action='store_true', default=False, required=False, help="search tree properties rather than study properties")
parser.add_argument('property')
args = parser.parse_args(sys.argv[1:])
study_prop = args.property
phy = Phylesystem()
out = codecs.getwriter('utf-8')(sys.stdout)
summarize_as_set = args.set
check_trees = args.tree
v_dict = defaultdict(int)


def process_val(o):
    if o is not None:
        if isinstance(o, dict):
            h = o.get('@href')
            if h is None:
                v = unicode(o)
            else:
                v = h
        else:
            v = unicode(o)
        if summarize_as_set:
            v_dict[v] += 1
        else:
            out.write(u'{i}: {v}\n'.format(i=study_id, v=v))

for study_id, n in phy.iter_study_objs():
    nexml = get_nexml_el(n)
    if check_trees:
        for trees_group_id, tree_id, tree in iter_trees(n):
            process_val(tree.get(study_prop))
    else:
        process_val(nexml.get(study_prop))
if summarize_as_set:
    as_list = [(v, k) for k, v in v_dict.items()]
    as_list.sort(reverse=True)
    for v, k in as_list:
        out.write(u'"{k}" (seen {v:d} times)\n'.format(k=k, v=v))
