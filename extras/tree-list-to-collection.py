#!/usr/bin/env python
from peyotl.collections_store import get_empty_collection
from peyotl.collections_store.validation import validate_collection
from peyotl import write_as_json
import sys

# Expecting a lot of lines like pg_2359_4962 for 'pg_2359', 'tree4962'
inp_fn = sys.argv[1]
with open(inp_fn, 'r') as inp:
    lines = []
    for line in inp:
        line = line.strip()
        if (not line) or (line == 'taxonomy'):
            continue
        assert line.endswith('.tre')
        frag = line[:-4]
        s = frag.split('_')
        study_id, tree_frag = '_'.join(s[:-1]), s[-1]
        tree_id = 'tree' + tree_frag
        lines.append((study_id, tree_id))
c = get_empty_collection()
d = c['decisions']
for pair in lines:
    d.append({'SHA': '',
              'decision': 'INCLUDED',
              'name': '',
              'studyID': pair[0],
              'treeID': pair[1]
              })

assert not (validate_collection(c)[0])
write_as_json(c, sys.stdout)
