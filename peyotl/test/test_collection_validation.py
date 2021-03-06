#! /usr/bin/env python
# from peyotl.nexson_syntax import detect_nexson_version, get_empty_nexson
from peyotl.collections_store import get_empty_collection
from peyotl.utility.str_util import UNICODE
from peyotl.collections_store.validation import validate_collection
from peyotl.test.support import pathmap
from peyotl.test.support.helper import testing_write_json, testing_read_json
from peyotl.utility import get_logger
import unittest
import sys
import os

_LOG = get_logger(__name__)


class TestCollectionValidator(unittest.TestCase):
    def testValidFilesPass(self):
        # just one test file for now
        msg = ''
        frag = 'collection-good.json'
        collection = pathmap.collection_obj(frag)
        aa = validate_collection(collection)
        errors = aa[0]
        for e in errors:
            _LOG.debug('unexpected error from {f}: {m}'.format(f=frag, m=UNICODE(e)))
        if len(errors) > 0:
            ofn = pathmap.collection_source_path(frag + '.output')
            testing_write_json(errors, ofn)
            msg = "File failed to validate cleanly. See {o}".format(o=ofn)
        self.assertEqual(len(errors), 0, msg)

    def testInvalidFilesFail(self):
        # just one test file for now
        msg = ''
        frag = 'collection-incomplete.json'
        inp = pathmap.collection_obj(frag)
        try:
            aa = validate_collection(inp)
            if len(aa) > 0:
                errors = aa[0]
                if len(errors) == 0:
                    ofn = pathmap.collection_source_path(frag + '.output')
                    testing_write_json(errors, ofn)
                    msg = "Failed to reject file. See {o}".format(o=str(msg))
                    self.assertTrue(False, msg)
        except:
            pass

    def testExpectedWarnings(self):
        msg = ''
        # compare test files (.input and .expected for each)
        # N.B. in some cases, python 2 and python 3 will have different output!
        for fn in pathmap.all_files(os.path.join('collections', 'warn_err')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                efn = frag + '.expected'
                # check for a python version-specific file, like 'foo.expected-py3'
                current_python_version = (sys.version_info > (3, 0)) and 'py3' or 'py2'
                versioned_efn = '{f}-{v}'.format(f=efn, v=current_python_version)
                if os.path.exists(versioned_efn):
                    efn = versioned_efn
                if os.path.exists(efn):
                    inp = testing_read_json(fn)
                    aa = validate_collection(inp)
                    errors = aa[0]
                    exp = testing_read_json(efn)
                    if errors != exp:
                        ofn = frag + '.output'
                        testing_write_json(errors, ofn)
                        msg = "Validation failed to produce expected outcome. Compare {o} and {e}".format(o=ofn, e=efn)
                    self.assertEqual(exp, errors, msg)
                else:
                    _LOG.warn('Expected output file "{f}" not found'.format(f=efn))

    def testCreated(self):
        c = get_empty_collection()
        aa = validate_collection(c)
        errors = aa[0]
        self.assertTrue(len(errors) == 0)


if __name__ == "__main__":
    unittest.main()
