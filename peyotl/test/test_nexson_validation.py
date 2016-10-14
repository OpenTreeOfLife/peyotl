#! /usr/bin/env python
from peyotl.nexson_syntax import detect_nexson_version, get_empty_nexson
from peyotl.utility.str_util import UNICODE
from peyotl.nexson_validation import validate_nexson
from peyotl.test.support import pathmap
from peyotl.test.support.helper import (testing_write_json,
                                        testing_read_json,
                                        testing_through_json,
                                        testing_dict_eq,
                                        testing_conv_key_unicode_literal)
from peyotl.utility import get_logger
import unittest
import os

_LOG = get_logger(__name__)

# round trip filename tuples
VALID_NEXSON_DIRS = ['9', 'otu', ]


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
                    _LOG.debug('unexpected error from {f}: {m}'.format(f=frag, m=UNICODE(e)))
                if len(annot.errors) > 0:
                    ofn = pathmap.nexson_source_path(frag + '.output')
                    ew_dict = annot.get_err_warn_summary_dict()
                    testing_write_json(ew_dict, ofn)
                    msg = "File failed to validate cleanly. See {o}".format(o=ofn)
                self.assertEqual(len(annot.errors), 0, msg)

    def testInvalidFilesFail(self):
        msg = ''
        for fn in pathmap.all_files(os.path.join('nexson', 'invalid')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                inp = testing_read_json(fn)
                try:
                    aa = validate_nexson(inp)
                except:
                    continue
                annot = aa[0]
                if len(annot.errors) == 0:
                    ofn = pathmap.nexson_source_path(frag + '.output')
                    ew_dict = annot.get_err_warn_summary_dict()
                    testing_write_json(ew_dict, ofn)
                    msg = "Failed to reject file. See {o}".format(o=str(msg))
                    self.assertTrue(False, msg)

    def testExpectedWarnings(self):
        msg = ''
        for fn in pathmap.all_files(os.path.join('nexson', 'warn_err')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                efn = frag + '.expected'
                if os.path.exists(efn):
                    inp = testing_read_json(fn)
                    aa = validate_nexson(inp)
                    annot = aa[0]
                    ew_dict = annot.get_err_warn_summary_dict()
                    ew_dict = testing_conv_key_unicode_literal(testing_through_json(ew_dict))
                    exp = testing_conv_key_unicode_literal(testing_read_json(efn))
                    if not testing_dict_eq(ew_dict, exp):
                        ofn = frag + '.output'
                        testing_write_json(ew_dict, ofn)
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
                    inp = testing_read_json(fn)
                    aa = validate_nexson(inp)
                    annot = aa[0]
                    ew_dict = annot.get_err_warn_summary_dict()
                    ew_dict = testing_through_json(ew_dict)
                    exp = testing_read_json(efn)
                    if not testing_dict_eq(ew_dict, exp):
                        ofn = frag + '.output'
                        testing_write_json(ew_dict, ofn)
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
