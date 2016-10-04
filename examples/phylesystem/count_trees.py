#!/usr/bin/env python
from __future__ import print_function
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.nexson_syntax import extract_tree_nexson
import sys
try:
    phylsys = Phylesystem()
except Exception as e:
    sys.stderr.write('count_trees.py: Exception: {}\n'.format(e.message))
    sys.exit('count_trees.py: There was a problem creating a wrapper around your phylesystem '
             'instance. Double check your configuration (see '
             'http://opentreeoflife.github.io/peyotl/configuration/ for info).')
try:
    print_freq = 500
    num_trees = 0
    num_studies = 0
    max_trees_per_study = 0
    biggest_study = None
    studies_without_trees = []
    sys.stderr.write('count_trees.py: beginning loop over studies...\n')
    for study_id, nexson in phylsys.iter_study_objs():
        num_studies += 1
        try:
            nt = len(extract_tree_nexson(nexson, tree_id=None))
        except:
            sys.stderr.write('Problem extracting trees from study {}'.format(study_id))
            raise
        if nt == 0:
            studies_without_trees.append(study_id)
        else:
            num_trees += nt
            if nt > max_trees_per_study:
                biggest_study = study_id
                max_trees_per_study = nt
        if num_studies % print_freq == 0:
            sys.stderr.write('   ...{d} studies read. Still going...\n'.format(d=num_studies))

except:
    sys.exit('Unexpected error in iteration, please report this bug.')

output = '''{s:d} = # studies
{e:d} = # studies without any trees
{t:d} = # trees total
{m:d} = maximum # trees in any study ({b})
The tree-less studies are: {a}
'''.format(s=num_studies,
           e=len(studies_without_trees),
           t=num_trees,
           m=max_trees_per_study,
           b=biggest_study,
           a=studies_without_trees)
print(output)
