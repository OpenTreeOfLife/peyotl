#!/usr/bin/env python
from peyotl.api import PhylesystemAPI
pa = PhylesystemAPI(get_from='api',
                    transform='server')
print(pa.get('pg_10',
             tree_id='tree3',
             subtree_id='ingroup',
             format='newick'))