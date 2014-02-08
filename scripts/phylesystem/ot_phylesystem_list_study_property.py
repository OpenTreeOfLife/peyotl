#!/usr/bin/env python
'''For every study that has the study-level property name 
which is passed in as a command line argument, the script prints out
the study ID and the property value.

For example:
    ot_phylesystem_list_study_property.py '^ot:studyPublication'

prints out the study's URL for each study that has this property set.
'''
from peyotl import phylesystem_study_objs
import codecs
import sys
out = codecs.getwriter('utf-8')(sys.stdout)
try:
    study_prop = sys.argv[1]
except:
    sys.exit(__doc__)
for study_id, n in phylesystem_study_objs():
    o = n.get(study_prop)
    if o is not None:
        if isinstance(o, dict):
            h = o.get('@href')
            if h is None:
                v = unicode(o)
            else:
                v = h
        else:
            v = unicode(o)
        out.write(u'{i}: {v}\n'.format(i=study_id, v=v))