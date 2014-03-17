#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
import unittest
import codecs
import json
from peyotl.nexson_syntax import read_as_json
from peyotl.test.support import pathmap

n = read_as_json(pathmap.json_source_path('1003.json'))

repodir="/Users/ejmctavish/Documents/projects/otapi/phylesystem_test"

class TestCreate(unittest.TestCase):
        gd=GitAction(repodir)
        gd.write_study(study_id="9999", content=n, branch="ejm_test")
        
if __name__ == "__main__":
    unittest.main()