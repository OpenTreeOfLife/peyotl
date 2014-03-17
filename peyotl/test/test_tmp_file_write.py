#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
import unittest
import codecs
import json

inpf = codecs.open('/Users/ejmctavish/Documents/projects/otapi/api.opentreeoflife.org/ws-tests/data/1003.json', 'rU', encoding='utf-8')
n = json.load(inpf)


repodir="/Users/ejmctavish/Documents/projects/otapi/phylesystem_test"
#jsonfi="/Users/ejmctavish/Documents/projects/otapi/peyotl/peyotl/test/data/nexson/9/v1.2.json"
#content=read_json(jsonfi)#.readlines()
#study_id='9'
#branch="ejm_test"

class TestCreate(unittest.TestCase):
        gd=GitAction(repodir)
        gd.write_study(study_id="9999", content=n, branch="ejm_test")
        
if __name__ == "__main__":
    unittest.main()