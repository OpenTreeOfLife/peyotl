#! /usr/bin/env python
from peyotl.nexson_validation import validate_nexson
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os
_LOG = get_logger(__name__)

# round trip filename tuples
VALID_NEXSON_DIRS = ['otu', '9', ]

class TestConvert(unittest.TestCase):
    def testValidFilesPass(self):
        format_list = ['1.2']
        for d in VALID_NEXSON_DIRS:
            for nf in format_list:
                frag = os.path.join(d, 'v{f}.json'.format(f=nf))
                nexson = pathmap.nexson_obj(frag)
                annot, adaptor = validate_nexson(nexson)
                for e in annot.errors:
                    _LOG.debug('unexpected error from {f}: {m}'.format(f=frag, m=unicode(e)))
                for e in annot.warnings:
                    _LOG.debug('unexpected warning from {f}: {m}'.format(f=frag, m=unicode(e)))
                self.assertEqual(len(annot.errors), 0)
                self.assertEqual(len(annot.warnings), 0)

if __name__ == "__main__":
    unittest.main()
