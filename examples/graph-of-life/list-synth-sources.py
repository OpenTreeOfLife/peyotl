#!/usr/bin/env python
'''Calls the treemachine services to get the list 
of sources in the current synthetic tree
'''
from peyotl.sugar import treemachine
import argparse
import sys
import os
description = __doc__
prog = os.path.split(sys.argv[0])[-1]
parser = argparse.ArgumentParser(prog=prog, description=description)
parser.add_argument('--fetch',
                    action='store_true',
                    default=False,
                    required=False,
                    help="download the newick for the source tree from treemachine")
args = parser.parse_args(sys.argv[1:])
download = args.fetch
out = sys.stdout

sources = treemachine.synthetic_tree_id_list
for src in sources:
    study_id, tree_id = src['study_id'], src.get('tree_id')
    concat = '{}_{}'.format(study_id, tree_id)
    out.write(concat)
    if download:
        if tree_id != 'taxonomy':
            resp = treemachine.get_source_tree(study_id=study_id,
                                                 tree_id=tree_id,
                                                 git_sha=src['git_sha'])
            newick = resp['newick']
            out.write('\t')
            out.write(str(newick))
    out.write('\n')