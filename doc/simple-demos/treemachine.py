#!/usr/bin/env python
from peyotl.sugar import treemachine as tm

ott_ids = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579, 267484,
           128308, 380453, 678579, 883864, 863991, 3898562, 23821, 673540, 122251, 106729, 1084532, 541659]
print(tm.get_synth_tree_pruned(ott_ids=ott_ids))
