#!/usr/bin/env python
'''reports the number of unmapped OTUS (to stderr) and (for all mapped OTUs)
reports the ^ot:originalLabel\t^ot:ottTaxonName to standard out
'''
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.nexson_syntax import get_nexml_el
from peyotl.manip import iter_otus
from collections import defaultdict
import argparse
import codecs
import sys
import os
description = __doc__
prog = os.path.split(sys.argv[0])[-1]
parser = argparse.ArgumentParser(prog=prog, description=description)
parser.add_argument('output')
args = parser.parse_args(sys.argv[1:])
if os.path.exists(args.output):
    sys.exit('{} already exists! Exiting...\n'.format(args.output))
phy = Phylesystem()
out = codecs.open(args.output, 'w', encoding='utf-8')
num_unmapped = 0

for study_id, n in phy.iter_study_objs():
    for og, otu_id, otu in iter_otus(n):
        if '^ot:ottTaxonName' in otu:
            out.write(u'{s}\t{o}\t{r}\t{m}\n'.format(s=study_id,
                                                    o=otu_id,
                                                    r=otu['^ot:originalLabel'],
                                                    m=otu['^ot:ottTaxonName']))
        else:
            num_unmapped += 1
sys.stderr.write('{n:d} unmapped otus\n'.format(n=num_unmapped))
