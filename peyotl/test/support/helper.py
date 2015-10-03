#!/usr/bin/env python
from peyotl.utility.str_util import is_str_type
import codecs
import json

def testing_read_json(fp):
    with codecs.open(fp, 'r', encoding='utf-8') as f:
        return json.load(f)
def testing_write_json(o, fp):
    with codecs.open(fp, 'w', encoding='utf-8') as fo:
        json.dump(o, fo, indent=2, sort_keys=True)
        fo.write('\n')
def testing_through_json(d):
    return json.loads(json.dumps(d))

def testing_dict_eq(a, b):
    if a == b:
        return True
    return False


def testing_conv_key_unicode_literal(d):
    r = {}
    if not isinstance(d, dict):
        return d
    for k, v in d.items():
        if isinstance(v, dict):
            r[k] = testing_conv_key_unicode_literal(v)
        elif isinstance(v, list):
            r[k] = [testing_conv_key_unicode_literal(i) for i in v]
        elif is_str_type(v) and v == 'unicode':
            r[k] = 'str'
        else:
            r[k] = v
    return r
