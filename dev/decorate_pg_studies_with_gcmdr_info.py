#!/usr/bin/env python
'''For the original round of synthesis (draft 22) the
studies came from phylografter, but the info about 
which ones should be included (ergo which were rooted correctly)
was stored in python scripts in gcmdr.

This script takes:
    1. a path to gcmdr, and reads that list of study+tree IDs; and

It uses the phylesystem_api wrapper in local mode to decorate the
studies (then requiring a git push after the script is run)

For every tree in the gcmdr set of trees ready for synthesis it:
    1. adds the treeID to the candidate for synthesis meta data field, and
    2. labels the rooting as biological (instead of arbitrary)


TreeID should be listed in "^ot:candidateTreeForSynthesis" property of
the study

In the tree:
    ^ot:unrootedTree should be set to false
    ^ot:specifiedRoot should be assigned the value of ^ot:rootNodeId
'''


from peyotl.api.phylesystem_api import PhylesystemAPI
from peyotl.nexson_syntax import extract_tree_nexson, \
                                 get_nexml_el, \
                                 read_as_json, \
                                 write_as_json
import sys
import os

gcmdr_repo = sys.argv[1]
if not os.path.isdir(gcmdr_repo):
    sys.exit('expecting the gcmdr dir as an arg')
sys.path.append(gcmdr_repo)
verbose = '-v' in sys.argv
dry_run = '--dry-run' in sys.argv
if dry_run:
    sys.stderr.write('Running in "read-only" mode')
# largely based on collect_study_ids.py in gcmdr 
from microbes import studytreelist as microbelist
from plants import studytreelist as plantslist
from metazoa import studytreelist as metalist
from fungi import studytreelist as fungilist

studytreelist = []
studytreelist.extend(plantslist)
studytreelist.extend(metalist)
studytreelist.extend(fungilist)
studytreelist.extend(microbelist)

study2tree = {}
for pair in studytreelist:
    study, tree = pair.split('_')
    if len(study) == 1:
        study = '0' + study
    study2tree.setdefault('pg_' + study, []).append('tree' + tree)


pa = PhylesystemAPI(get_from='local')
raw_phylsys = pa.phylesystem_obj
nexson_version = raw_phylsys.repo_nexml2json
for study_id, tree_list in study2tree.items():
    if verbose:
        sys.stderr.write('treelist={t} for study {s}.\n'.format(t=str(tree_list), s=study_id))
    try:
        fp = raw_phylsys.get_filepath_for_study(study_id)
        blob = read_as_json(fp)

        nex = get_nexml_el(blob)
        prev = nex.setdefault('^ot:candidateTreeForSynthesis', [])
        for tree_id in tree_list:
            if tree_id not in prev:
                prev.append(tree_id)
            i_t_o_list = extract_tree_nexson(blob, tree_id, nexson_version)
            if not i_t_o_list:
                sys.stderr.write('tree {t} of study {s} not found !!!\n'.format(t=tree_id, s=study_id))
            for tid, tree, otus_group in i_t_o_list:
                tree['^ot:unrootedTree'] = False
                tree['^ot:specifiedRoot'] = tree['^ot:rootNodeId']
        if not dry_run:
            write_as_json(blob, fp)
        
    except KeyError:
        sys.stderr.write('study {} not found !!!\n'.format(study_id))