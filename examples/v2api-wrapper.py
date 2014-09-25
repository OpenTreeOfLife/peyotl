#!/usr/bin/env python
from peyotl.api import APIWrapper
ot = APIWrapper()
r = ot.tnrs.match_names([#'Canis lupus familiaris',
                         'Canidae',
                         'Vulpes vulpes',
                         'Equus',
                         'Dasypus novemcinctus'
                         #'Mammalia',
                         ], context_name='Animals')
print r
ot_ids = [i['matches'][0]['ot:ottId'] for i in r['results']]
print ot_ids
print ot.tree_of_life.induced_subtree(ott_ids=ot_ids)
