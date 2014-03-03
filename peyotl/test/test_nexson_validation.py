#! /usr/bin/env python
from peyotl.nexson_validation import validate_nexson
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import codecs
import json
import os
_LOG = get_logger(__name__)

# round trip filename tuples
VALID_NEXSON_DIRS = ['otu', '9', ]

def read_json(fp):
    return json.load(codecs.open(fp, 'rU', encoding='utf-8'))
def write_json(o, fp):
    with codecs.open(fp, 'w', encoding='utf-8') as fo:
        json.dump(o, fo, indent=2, sort_keys=True)
        fo.write('\n')
def through_json(d):
    return json.loads(json.dumps(d))
def dict_eq(a, b):
    if a == b:
        return True
    ka, kb = a.keys(), b.keys()
    ka.sort()
    kb.sort()
    if ka != kb:
        _LOG.debug('keys "{a}" != "{b}"'.format(a=ka, b=kb))
    for k in ka:
        va = a[k]
        vb = b[k]
        if va != vb:
            _LOG.debug('value for {k}: "{a}" != "{b}"'.format(k=k, a=va, b=vb))
    return False

class TestConvert(unittest.TestCase):
    def testValidFilesPass(self):
        format_list = ['1.2']
        for d in VALID_NEXSON_DIRS:
            for nf in format_list:
                frag = os.path.join(d, 'v{f}.json'.format(f=nf))
                nexson = pathmap.nexson_obj(frag)
                aa = validate_nexson(nexson)
                annot = aa[0]
                for e in annot.errors:
                    _LOG.debug('unexpected error from {f}: {m}'.format(f=frag, m=unicode(e)))
                for e in annot.warnings:
                    _LOG.debug('unexpected warning from {f}: {m}'.format(f=frag, m=unicode(e)))
                self.assertEqual(len(annot.errors), 0)
                self.assertEqual(len(annot.warnings), 0)
    def testExpectedWarnings(self):
        for fn in pathmap.all_files(os.path.join('nexson', 'warn_err')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                efn = frag + '.expected'
                if os.path.exists(efn):
                    inp = read_json(fn)
                    vp = validate_nexson(inp)
                    v = vp[0]
                    em_dict = v.get_err_warn_summary_dict()
                    em_dict = through_json(em_dict)
                    exp = read_json(efn)
                    if not dict_eq(em_dict, exp):
                        ofn = frag + '.output'
                        write_json(em_dict, ofn)
                        m = "Validation failed. Compare {o} and {e}".format(o=ofn, e=efn)
                        self.assertEqual(exp, em_dict, m)


                else:
                    _LOG.warn('Expected output file "{f}" not found'.format(f=efn))

if __name__ == "__main__":
    unittest.main()
