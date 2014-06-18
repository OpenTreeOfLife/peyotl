#!/usr/bin/env python
from peyotl.nexson_syntax import read_as_json, write_as_json
from peyotl import get_logger

import sys
import re
_LOG = get_logger('evaluate-auto-mapping')
if len(sys.argv) != 4:
    sys.exit('expecting an input file path for the JSON mapping file and 2 output file for the plausible and implausible unmapped')
inf = sys.argv[1]
poutf = sys.argv[2]
ioutf = sys.argv[3]
_LOG.debug('Reading test cases from "{}"'.format(inf))
test_case_dict = read_as_json(inf)

possible = {}
impossible = {}

np = 0
ni = 0
for study_id, otu_list in test_case_dict.items():
    p = []
    i = []
    for el in otu_list:
        matches = el[1]
        orig = el[0].lower()
        is_plausible = False
        for m in matches:
            if m.lower() in orig:
                is_plausible = True
                break
        if is_plausible:
            p.append(el)
        else:
            i.append(el)
    if p:
        possible[study_id] = p
        np += len(p)
    if i:
        impossible[study_id] = i
        ni += len(i)

write_as_json(possible, poutf)
write_as_json(impossible, ioutf)
_LOG.debug('%d promising mappings written to %s.' % (np, poutf))
_LOG.debug('%d implausible mapping written to %s' % (ni, ioutf))
