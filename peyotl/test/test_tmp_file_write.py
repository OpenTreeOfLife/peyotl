#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
import unittest
import codecs
import json
from peyotl.nexson_syntax import read_as_json

n = read_asjson(pathmap.nexson_source_path('1003'))

repodir="/Users/ejmctavish/Documents/projects/otapi/phylesystem_test"

class TestCreate(unittest.TestCase):
        gd=GitAction(repodir)
        gd.write_study(study_id="9999", content=n, branch="ejm_test")
        
if __name__ == "__main__":
    unittest.main()