#! /usr/bin/env python
from peyotl.phylesystem.git_actions import GitAction
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

class TestCreate(unittest.TestCase):
    @unittest.skipIf(not HAS_LOCAL_PHYLESYSTEM_REPOS, 'only available if you are have a [phylesystem] section with "parent" variable in your peyotl config')
    def testWriteStudy(self):
        self.reponame = list(get_repos().keys())[0]
        self.repodir = get_repos()[self.reponame]
        GitAction(self.repodir)

if __name__ == "__main__":
    unittest.main()
