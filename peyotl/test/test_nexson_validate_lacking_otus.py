#! /usr/bin/env python
from peyotl.nexson_validation import validate_nexson
from peyotl.test.support.helper import testing_write_json, testing_read_json
from peyotl.test.support import pathmap
from peyotl.utility import get_logger
import unittest
import os

_LOG = get_logger(__name__)

# round trip filename tuples
VALID_NEXSON_DIRS = ['9', 'otu', ]


class TestConvert(unittest.TestCase):
    def testInvalidFilesFail(self):
        msg = ''
        for fn in pathmap.all_files(os.path.join('nexson', 'lacking_otus')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                inp = testing_read_json(fn)
                aa = validate_nexson(inp)
                annot = aa[0]
                if len(annot.errors) == 0:
                    ofn = pathmap.nexson_source_path(frag + '.output')
                    ew_dict = annot.get_err_warn_summary_dict()
                    testing_write_json(ew_dict, ofn)
                    msg = "Failed to reject file. See {o}".format(o=str(msg))
                    self.assertTrue(False, msg)


if __name__ == "__main__":
    unittest.main()
