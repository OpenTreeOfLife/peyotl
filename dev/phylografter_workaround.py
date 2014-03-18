#!/usr/bin/env python
import sys, json, codecs
from peyotl import write_as_json
inpfn = sys.argv[1]
outfn = sys.argv[2]
inp = codecs.open(inpfn, mode='rU', encoding='utf-8')
out = codecs.open(outfn, mode='w', encoding='utf-8')
obj = json.load(inp)
def rec_resource_meta(blob, k):
    if k == 'meta' and isinstance(blob, dict):
        if blob.get('@xsi:type') == 'nex:ResourceMeta':
            if (blob.get('@rel') is None):
                p = blob.get('@property')
                if p is not None:
                    del blob['@property']
                    blob['@rel'] = p
                    print blob
    if isinstance(blob, list):
        for i in blob:
            rec_resource_meta(i, k)
    else:
        for inner_k, v in blob.items():
            if isinstance(v, list) or isinstance(v, dict):
                rec_resource_meta(v, inner_k)

def coerce_boolean(blob, k):
    '''Booleans emitted as "true" or "false"
    for "@root" and "ot:isLeaf" meta
    '''
    if isinstance(blob, dict):
        if k == 'meta':
            if blob.get('@property') == 'ot:isLeaf':
                v = blob.get('$')
                try:
                    if v.lower() == "true":
                        blob['$'] = True
                    elif v.lower == "false":
                        blob['$'] = False
                except:
                    pass
        else:
            r = blob.get('@root')
            if r is not None:
                try:
                    if r.lower() == "true":
                        blob['@root'] = True
                    elif r.lower == "false":
                        blob['@root'] = False
                except:
                    pass
        for inner_k, v in blob.items():
            if isinstance(v, list) or isinstance(v, dict):
                coerce_boolean(v, inner_k)
    elif isinstance(blob, list):
        for i in blob:
            coerce_boolean(i, k)
rec_resource_meta(obj, 'root')
coerce_boolean(obj, 'root')

write_as_json(obj, out)
