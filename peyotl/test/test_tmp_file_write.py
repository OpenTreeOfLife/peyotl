#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
from peyotl import phylesystem
import unittest
from peyotl.nexson_syntax import read_as_json
from peyotl.test.support import pathmap
from peyotl.phylesystem import get_repos
try:
    r = get_repos()
    HAS_LOCAL_PHYLESYSTEM_REPOS = True
except:
    HAS_LOCAL_PHYLESYSTEM_REPOS = False

n = read_as_json(pathmap.json_source_path('1003.json'))

#reponame = phylesystem.get_repos().keys()[0]
#repodir = phylesystem.get_repos()[reponame]

class TestCreate(unittest.TestCase):
    @unittest.skipIf(not HAS_LOCAL_PHYLESYSTEM_REPOS, 'only available if you are have a [phylesystem] section with "parent" variable in your peyotl config')
    def testWriteStudy(self):
        self.reponame = phylesystem.get_repos().keys()[0]
        self.repodir = phylesystem.get_repos()[self.reponame]
        GitAction(self.repodir)
        #gd.write_study(study_id="1003", content=n, branch="git_actions_test_1003")

if __name__ == "__main__":
    unittest.main()
