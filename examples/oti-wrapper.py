#!/usr/bin/env python
from peyotl.api import APIWrapper
oti = APIWrapper().oti
print(oti.study_search_term_set)
print(oti.tree_search_term_set))
print(oti.find_trees({'ot:ottTaxonName': 'Aponogeton ulvaceus'}))
print(oti.find_trees(ottTaxonName='Aponogeton ulvaceus'))
