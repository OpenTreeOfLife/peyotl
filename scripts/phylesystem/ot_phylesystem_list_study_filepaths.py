#!/usr/bin/env python
'''Lists the absolute filepath for every study in the
phylesystem directories that the peyotl library can 
find (see README for discussion of configuration).
'''
from peyotl import phylesystem_studies
for i in phylesystem_studies():
    print i