#! /usr/bin/env python
from peyotl.nexson_syntax import detect_nexson_version, get_empty_nexson
from peyotl.nexson_validation import validate_nexson
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import codecs
import json
import os
_LOG = get_logger(__name__)

# round trip filename tuples
VALID_NEXSON_DIRS = ['9', 'otu', ]

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
    return False
    # ka, kb = a.keys(), b.keys()
    # ka.sort()
    # kb.sort()
    # if ka != kb:
    #     _LOG.debug('keys "{a}" != "{b}"'.format(a=ka, b=kb))
    # for k in ka:
    #     va = a[k]
    #     vb = b[k]
    #     if va != vb:
    #         _LOG.debug('value for {k}: "{a}" != "{b}"'.format(k=k, a=va, b=vb))
    # return False

class TestConvert(unittest.TestCase):
    def testDetectVersion(self):
        o = pathmap.nexson_obj('invalid/bad_version.json.input')
        v = detect_nexson_version(o)
        self.assertEqual(v, '1.3.1')

    def testValidFilesPass(self):
        format_list = ['1.2']
        msg = ''
        for d in VALID_NEXSON_DIRS:
            for nf in format_list:
                frag = os.path.join(d, 'v{f}.json'.format(f=nf))
                nexson = pathmap.nexson_obj(frag)
                aa = validate_nexson(nexson)
                annot = aa[0]
                for e in annot.errors:
                    _LOG.debug('unexpected error from {f}: {m}'.format(f=frag, m=unicode(e)))
                if len(annot.errors) > 0:
                    ofn = pathmap.nexson_source_path(frag + '.output')
                    ew_dict = annot.get_err_warn_summary_dict()
                    write_json(ew_dict, ofn)
                    msg = "File failed to validate cleanly. See {o}".format(o=ofn)
                self.assertEqual(len(annot.errors), 0, msg)
    def testInvalidFilesFail(self):
        msg = ''
        for fn in pathmap.all_files(os.path.join('nexson', 'invalid')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                inp = read_json(fn)
                try:
                    aa = validate_nexson(inp)
                except:
                    continue
                annot = aa[0]
                if len(annot.errors) == 0:
                    ofn = pathmap.nexson_source_path(frag + '.output')
                    ew_dict = annot.get_err_warn_summary_dict()
                    write_json(ew_dict, ofn)
                    msg = "Failed to reject file. See {o}".format(o=str(msg))
                    self.assertTrue(False, msg)
    def testExpectedWarnings(self):
        msg = ''
        for fn in pathmap.all_files(os.path.join('nexson', 'warn_err')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                efn = frag + '.expected'
                if os.path.exists(efn):
                    inp = read_json(fn)
                    aa = validate_nexson(inp)
                    annot = aa[0]
                    ew_dict = annot.get_err_warn_summary_dict()
                    ew_dict = through_json(ew_dict)
                    exp = read_json(efn)
                    if not dict_eq(ew_dict, exp):
                        ofn = frag + '.output'
                        write_json(ew_dict, ofn)
                        msg = "Validation failed to produce expected outcome. Compare {o} and {e}".format(o=ofn, e=efn)
                    self.assertDictEqual(exp, ew_dict, msg)
                else:
                    _LOG.warn('Expected output file "{f}" not found'.format(f=efn))
    def testOldExpectedWarnings(self):
        msg = ''
        for fn in pathmap.all_files(os.path.join('nexson', 'old-tests')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                efn = frag + '.expected'
                if os.path.exists(efn):
                    inp = read_json(fn)
                    aa = validate_nexson(inp)
                    annot = aa[0]
                    ew_dict = annot.get_err_warn_summary_dict()
                    ew_dict = through_json(ew_dict)
                    exp = read_json(efn)
                    if not dict_eq(ew_dict, exp):
                        ofn = frag + '.output'
                        write_json(ew_dict, ofn)
                        msg = "Validation failed to produce expected outcome. Compare {o} and {e}".format(o=ofn, e=efn)
                    self.assertDictEqual(exp, ew_dict, msg)
                else:
                    _LOG.warn('Expected output file "{f}" not found'.format(f=efn))
    def testCreated(self):
        b = get_empty_nexson()
        aa = validate_nexson(b)
        annot = aa[0]
        self.assertFalse(annot.has_error())
        b = get_empty_nexson(include_cc0=True)
        aa = validate_nexson(b)
        annot = aa[0]
        self.assertFalse(annot.has_error())

if __name__ == "__main__":
    unittest.main()
