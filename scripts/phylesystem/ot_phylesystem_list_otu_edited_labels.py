#!/usr/bin/env python
'''Examines each otu in each study. Prints out any
case in which the otu label is not the ot:originalLabel or
the ot:ottTaxonName'''
tax_prop_name = '^ot:ottTaxonName'
orig_prop_name = '^ot:originalLabel'
label_prop_name = '@label'
from peyotl import gen_otu_dict, iter_tree, iter_node
from peyotl.phylesystem import Phylesystem
import codecs
import sys
phy = Phylesystem()

out = codecs.getwriter('utf-8')(sys.stdout)
for study_id, n in phy.iter_study_objs():
    otu_dict = gen_otu_dict(n)
    o_dict = {}
    for oid, o in otu_dict.items():
        try:
            lab = o[label_prop_name]
            orig = o[orig_prop_name]
            o_dict[oid] = [orig, None, lab]
        except:
            pass
    del otu_dict
    for tree in iter_tree(n):
        for node in iter_node(tree):
            oid = node.get('@otu')
            if oid is not None:
                ott = node.get(tax_prop_name)
                if ott is not None:
                    try:
                        o_dict[oid][1] = ott
                    except:
                        e = 'study {f} node {n} refers to otu {o} which is not found.\n'
                        m = e.format(f=study_id, n=node.get('@id'), o=oid)
                        sys.stderr.write(m)
    for oid, v in o_dict.items():
        t = v[1]
        l = v[2]
        if l and (t != l):
            orig = v[0]
            if (l != orig) and (t is None):
                s = u'study {f}: {i} {ln}="{l}" {on}="{o}"\n'
                m = s.format(f=study_id, i=oid, l=l, o=orig,
                             ln=label_prop_name, on=orig_prop_name)
                out.write(m)
            elif t is not None:
                s = u'study {f}: {i} {ln}="{l}" {tn}="{t}" {on}="{o}"\n'
                m = s.format(f=study_id, i=oid, l=l, t=t, o=orig,
                             ln=label_prop_name, tn=tax_prop_name, on=orig_prop_name)
                out.write(m)