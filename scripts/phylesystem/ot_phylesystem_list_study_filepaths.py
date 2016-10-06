#!/usr/bin/env python
"""Lists the absolute filepath for every study in the
phylesystem directories that the peyotl library can
find (see README for discussion of configuration).
"""
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
phy = Phylesystem()
for study_id, filepath in phy.iter_study_filepaths():
    print(filepath)
