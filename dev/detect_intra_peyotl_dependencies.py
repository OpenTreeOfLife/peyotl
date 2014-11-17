#!/usr/bin/env python
from subprocess import check_output
import sys
import os
import re
script_path = os.path.abspath(sys.argv[0])
dev_path = os.path.split(script_path)[0]
par_path = os.path.split(dev_path)[0]
peyotl_path = os.path.join(par_path, 'peyotl')
c = check_output(['grep', '-r', '^from peyotl.* import ', peyotl_path])
mod_dep_mod = re.compile(r'^([a-zA-Z0-9._]+)[:/]\S*from peyotl\.([_a-zA-Z0-9]+)')
d = {}
for line in c.split('\n'):
    if '~' in line or '.pyc' in line:
        continue
    if line.startswith(peyotl_path):
        trimmed = line[1 + len(peyotl_path):-1]
        mt = mod_dep_mod.match(trimmed)
        assert mt
        mod, dep = mt.group(1), mt.group(2)
        gd = d.setdefault(mod, set())
        gd.add(dep)

ml = list(d.keys())
ml.sort()
for mod in ml:
    dep_set = d[mod]
    x = [i for i in dep_set if i != mod]
    x.sort()
    print '{m} depends on: "{d}"'.format(m=mod, d='", "'.join(x))
