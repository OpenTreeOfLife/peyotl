#!/usr/bin/env python
'''Trying to make a report that corresponds to
    https://github.com/OpenTreeOfLife/germinator/wiki/Overview-of-repository-statistics
'''
import time
start_clock = time.time()
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.nexson_syntax import get_nexml_el
from peyotl import gen_otu_dict, iter_node
from peyotl.manip import iter_trees
import codecs
import json
import sys

out = codecs.getwriter('utf-8')(sys.stdout)

phy = Phylesystem()
# Start all of the properties for the report at 0
report_properties = ['reported_study_count',
                     'study_count',
                     'OTU_count',
                     'unmapped_OTU_count',
                     'unique_OTU_count',
                     'nominated_study_count',
                     'nominated_study_OTU_count',
                     'nominated_study_unique_OTU_count',
                     'nominated_study_unmapped_OTU_count',
                     'run_time']
reported_study_count = 0
study_count = 0
OTU_count = 0
unmapped_OTU_count = 0
unique_OTU_count = 0
nominated_study_count = 0
nominated_study_OTU_count = 0
nominated_study_unique_OTU_count = 0
nominated_study_unmapped_OTU_count = 0
run_time = 0



ott_id_set = set()
nominated_ott_id_set = set()
for study_id, n in phy.iter_study_objs():
    reported_study_count += 1
    otu_dict = gen_otu_dict(n)
    if not bool(otu_dict):
        continue
    nex_obj = get_nexml_el(n)
    study_count += 1
    not_intended_for_synth = nex_obj.get('^ot:notIntendedForSynthesis')
    intended_for_synth = (not_intended_for_synth is None) or (not_intended_for_synth is False)
    if intended_for_synth:
        nominated_study_count += 1
        nominated_study_OTU_count += len(otu_dict)
    OTU_count += len(otu_dict)

    for oid, o in otu_dict.items():
        ott_id = o.get('^ot:ottId')
        if ott_id is None:
            unmapped_OTU_count += 1
            if intended_for_synth:
                nominated_study_unmapped_OTU_count += 1
        else:
            ott_id_set.add(ott_id)
            if intended_for_synth:
                nominated_ott_id_set.add(ott_id)
unique_OTU_count = len(ott_id_set)
nominated_study_unique_OTU_count = len(nominated_ott_id_set)
end_clock = time.time()
run_time = end_clock - start_clock

#################################################
# write variables in local scope in a JSON blob
report = {}
for prop in report_properties:
    report[prop] = locals()[prop]
json.dump(report, out, sort_keys=True, indent=2, separators=(',',': '))
out.write('\n')