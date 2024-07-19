#!/usr/bin/env python
import sys, json, codecs
from peyotl.phylografter.nexson_workaround import workaround_phylografter_export_diffs
inpfn = sys.argv[1]
outfn = sys.argv[2]
with codecs.open(inpfn, mode='r', encoding='utf-8') as inp:
    obj = json.load(inp)
workaround_phylografter_export_diffs(obj, outfn)
