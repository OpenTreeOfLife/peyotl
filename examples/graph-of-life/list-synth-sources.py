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
parser.add_argument('--nexus',
                    action='store_true',
                    default=False,
                    required=False,
                    help="(if --fetch is used). format results as NEXUS")
args = parser.parse_args(sys.argv[1:])
download = args.fetch
nexus = args.nexus
out = sys.stdout

if nexus:
    out.write('#NEXUS\nBEGIN TREES;\n')
sources = treemachine.synthetic_tree_id_list

if download:
    if nexus:
        pref = 'TREE {} = [&R] '
    else:
        pref = '{}\t'
else:
    pref = '{}'
for src in sources:
    out.flush()
    study_id, tree_id = src['study_id'], src.get('tree_id', '')
    concat = '{}_{}'.format(study_id, tree_id)
    newick = ''
    if download:
        try:
            if tree_id != 'taxonomy':
                resp = treemachine.get_source_tree(study_id=study_id,
                                                     tree_id=tree_id,
                                                     git_sha=src['git_sha'])
                newick = resp['newick']
        except:
            sys.stderr.write('Download of {} failed.\n'.format(concat))
            continue
    if tree_id == 'taxonomy':
        if nexus:
            out.write('[taxonomy\t]\n')
        else:
            out.write('taxonomy\n')
    else:
        out.write(pref.format(concat))
        if download:
            out.write(newick)
        out.write('\n')
