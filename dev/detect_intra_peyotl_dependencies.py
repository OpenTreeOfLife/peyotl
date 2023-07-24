#!/usr/bin/env python
from subprocess import check_output
import sys
import os
import re

if '-h' in sys.argv:
    sys.stdout.write('''script to parse import statements in peyotl to determine
which subpackages depend on which other parts.

Args:
    -d writes the output in dot format.
    -s simplifies the output by only listing a higher level dependency (if that
        dependency includes a lower level one)

We want peyotl to be series of modules rather than an intertangled mass. Most
    packages depend on peyotl.utility and many will depend on peyotl.nexson_syntax
    But we really want the dependeny graph to be have no directed cycles (in which 2
    subpackages depend on each other).

This script relies on the code using the "from peyotl... import" syntax (which we try
    to conform to).

''')
    sys.exit(0)
write_dot = '-d' in sys.argv
simplify = '-s' in sys.argv
ext = None
for f in sys.argv[1:]:
    if f.startswith('-e'):
        ext = f[2:]
ext_deps = {}
if ext:
    with open(ext, 'r') as fo:
        d = []
        ext_key = None
        for line in fo:
            if line.startswith(' '):
                d.append(line.strip())
            else:
                if d:
                    assert ext_key
                    ext_deps[ext_key] = d
                    d = []
                ext_key = line.strip().split('/')[-1]

    if d:
        assert ext_key
        ext_deps[ext_key] = d
out = sys.stdout
script_path = os.path.abspath(sys.argv[0])
dev_path = os.path.split(script_path)[0]
par_path = os.path.split(dev_path)[0]
peyotl_path = os.path.join(par_path, 'peyotl')
c = check_output(['grep', '-r', '^ *from peyotl.* import ', peyotl_path])
mod_dep_mod = re.compile(r'^ *([a-zA-Z0-9._]+)[:/]\S* *from peyotl\.([_a-zA-Z0-9]+)')
d = {}
sub_els = os.listdir(peyotl_path)
for line in c.split('\n'):
    if '~' in line or '.pyc' in line:
        continue
    if line.startswith(peyotl_path):
        trimmed = line[1 + len(peyotl_path):-1]
        mt = mod_dep_mod.match(trimmed)
        sys.stderr.write('trimmed = ' + trimmed + '\n')
        assert mt
        mod, dep = mt.group(1), mt.group(2)
        if mod != dep:
            if mod.endswith('.py'):
                mod = mod[:-3]
            if dep.endswith('.py'):
                dep = dep[:-3]
            gd = d.setdefault(mod, set())
            gd.add(dep)
for i in sub_els:
    if '~' in i or i.endswith('.pyc'):
        continue
    if i not in d:
        d[i] = {}


def simplify_list_of_deps(dep_dict, dep_list):
    remove = set()
    for i in dep_list:
        for j in dep_list:
            if (i != j) and (i in dep_dict.get(j, {})):
                # sys.stderr.write('{i} removed because it is in {j} deps\n'.format(i=i, j=j))
                remove.add(i)
    return set([i for i in dep_list if i not in remove])


for suppress in ['test', '__init__']:
    if suppress in d:
        del d[suppress]
if simplify:
    r = {}
    for k, v in d.items():
        r[k] = simplify_list_of_deps(d, v)
        # sys.stderr.write(k + ' -> ' + str(v) + '\n to    -> ' + str(r[k]) + '\n')
    d = r

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
    if ext_deps:
        for k, v in ext_deps.items():
            if v:
                v.sort()
                out.write('   "{m}" [shape=box,style=filled,color="#BBBBFF"] ;\n'.format(m=k))
                for edep in v:
                    out.write('   edge [color=blue] ;\n   "{m}" -> "{e}" ;\n'.format(m=k, e=edep))
    out.write('}\n')
else:
    for mod in ml:
        dep_set = d[mod]
        x = [i for i in dep_set if i != mod]
        x.sort()
        print('{m} depends on: "{d}"'.format(m=mod, d='", "'.join(x)))
