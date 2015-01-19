#!/usr/bin/env python
'''For every study that has the study-level property name 
which is passed in as a command line argument, the script prints out
the study ID and the property value.

For example:
    ot_phylesystem_list_propery_values.py '^ot:studyPublication'

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
parser.add_argument('--report-ids', action='store_true', default=False, required=False, help="report as value -> id list")
parser.add_argument('property')
args = parser.parse_args(sys.argv[1:])
study_prop = args.property
phy = Phylesystem()
out = codecs.getwriter('utf-8')(sys.stdout)
report_ids = args.report_ids
summarize_as_set = args.set
check_trees = args.tree
if report_ids:
    v_dict = {}
else:
    v_dict = defaultdict(int)

def process_val(v, id_str):
    if v is not None:
        if report_ids:
            v_dict.setdefault(v, []).append(id_str)
        elif summarize_as_set:
            v_dict[v] += 1
        else:
            out.write(u'{i}: {v}\n'.format(i=study_id, v=v))

for study_id, n in phy.iter_study_objs():
    nexml = get_nexml_el(n)
    if check_trees:
        for trees_group_id, tree_id, tree in iter_trees(n):
            id_str = 'study: {s} tree: {t}'.format(s=study_id, t=tree_id)
            process_val(tree.get(study_prop), id_str)
    else:
        process_val(nexml.get(study_prop), study_id)

if report_ids:
    as_list = [(len(v), k, v) for k, v in v_dict.items()]
    as_list.sort(reverse=True)
    for n, k, v in as_list:
        out.write(u'{k}\tseen {n:d} times\t{v}\n'.format(k=k, n=n, v='\t'.join(v)))
elif summarize_as_set:
    as_list = [(v, k) for k, v in v_dict.items()]
    as_list.sort(reverse=True)
    for v, k in as_list:
        out.write(u'"{k}" (seen {v:d} times)\n'.format(k=k, v=v))
