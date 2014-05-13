#!/usr/bin/env python
import sys, json, codecs
from peyotl.phylografter.nexson_workaround import workaround_phylografter_export_diffs
inpfn = sys.argv[1]
outfn = sys.argv[2]
inp = codecs.open(inpfn, mode='rU', encoding='utf-8')
obj = json.load(inp)
workaround_phylografter_export_diffs(obj, outfn)