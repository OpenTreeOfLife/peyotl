#!/usr/bin/env python
from subprocess import check_output
import sys
import os
import re
if '-h' in sys.argv:
    sys.stdout.write('''script to parse import statements in peyotl to determine
which subpackages depend on which other parts.

Args: -d writes the output in dot format.

We want peyotl to be series of modules rather than an intertangled mass. Most
    packages depend on peyotl.utility and many will depend on peyotl.nexson_syntax
    But we really want the dependeny graph to be have no directed cycles (in which 2
    subpackages depend on each other).

This script relies on the code using the "from peyotl... import" syntax (which we try
    to conform to).

''')
    sys.exit(0)
write_dot = '-d' in sys.argv
out = sys.stdout
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

for i in os.listdir(peyotl_path):
    if '~' in i or i.endswith('.pyc'):
        continue
    if i not in d:
        d[i] = {}

for suppress in ['test', '__init__.py']:
    if suppress in d:
        del d[suppress]
ml = list(d.keys())
ml.sort()

if write_dot:
    out.write('digraph peyotldep {\n')
    for mod in ml:
        dep_set = d[mod]
        x = [i for i in dep_set if i != mod]
        x.sort()
        for dep in x:
            out.write('  "{m}" -> "{d}";\n'.format(m=mod, d=dep))
    out.write('}\n')
else:
    for mod in ml:
        dep_set = d[mod]
        x = [i for i in dep_set if i != mod]
        x.sort()
        print '{m} depends on: "{d}"'.format(m=mod, d='", "'.join(x))
