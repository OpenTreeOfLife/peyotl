#! /usr/bin/env python
from peyotl.nexson_validation import ot_validate
from peyotl.utility import get_logger
from peyotl.phylesystem.git_workflows import validate_and_convert_nexson
import unittest
import os
from nexson.test.support.pathmap import get_test_path_mapper

pathmap = get_test_path_mapper()

_LOG = get_logger(__name__)

# round trip filename tuples
VALID_NEXSON_DIRS = ['9', 'otu', ]


class TestConvert(unittest.TestCase):
    def testValidFilesPass(self):
        format_list = ['1.0', '1.2']
        TESTS_WITH_GT_ONE_TREE = ['9']
        for d in TESTS_WITH_GT_ONE_TREE:
            for nf in format_list:
                frag = os.path.join(d, 'v{f}.json'.format(f=nf))
                nexson = pathmap.nexson_obj(frag)
                annotation = ot_validate(nexson)[0]
                self.assertTrue(annotation['annotationEvent']['@passedChecks'])
                annotation = ot_validate(nexson, max_num_trees_per_study=1)[0]
                self.assertFalse(annotation['annotationEvent']['@passedChecks'])
                annotation = ot_validate(nexson, max_num_trees_per_study=1)[0]
                self.assertFalse(annotation['annotationEvent']['@passedChecks'])
                bundle = validate_and_convert_nexson(nexson,
                                                     nf,
                                                     allow_invalid=True,
                                                     max_num_trees_per_study=1)
                annotation = bundle[1]
                self.assertFalse(annotation['annotationEvent']['@passedChecks'])


if __name__ == "__main__":
    unittest.main()
