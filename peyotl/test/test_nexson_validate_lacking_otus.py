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
    return json.load(codecs.open(fp, 'r', encoding='utf-8'))
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

class TestConvert(unittest.TestCase):
    def testInvalidFilesFail(self):
        msg = ''
        for fn in pathmap.all_files(os.path.join('nexson', 'lacking_otus')):
            if fn.endswith('.input'):
                frag = fn[:-len('.input')]
                inp = read_json(fn)
                aa = validate_nexson(inp)
                annot = aa[0]
                if len(annot.errors) == 0:
                    ofn = pathmap.nexson_source_path(frag + '.output')
                    ew_dict = annot.get_err_warn_summary_dict()
                    write_json(ew_dict, ofn)
                    msg = "Failed to reject file. See {o}".format(o=str(msg))
                    self.assertTrue(False, msg)

if __name__ == "__main__":
    unittest.main()
