# lists all of the study-level and tree-level properties across the phylesystem

# peyotl setup
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from __future__ import print_function
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.api.phylesystem_api import PhylesystemAPI
from peyotl.manip import iter_trees
from peyotl.nexson_syntax import get_nexml_el


def create_phylesystem_obj():
    # create connection to local phylesystem
    phylesystem_api_wrapper = PhylesystemAPI(get_from='local')
    phylesystem = phylesystem_api_wrapper.phylesystem_obj
    return phylesystem


if __name__ == "__main__":
    counter = 0
    limit = None
    tree_key_set = set()
    study_key_set = set()
    phy = create_phylesystem_obj()
    for study_id, studyobj in phy.iter_study_objs():
        for k in studyobj['nexml'].keys():
            study_key_set.add(k)
        for trees_group_id, tree_id, tree in iter_trees(studyobj):
            for k in tree.keys():
                tree_key_set.add(k)
        counter += 1
        if (counter % 100 == 0):
            print("Read {n} studies".format(n=counter))
        if (limit and counter > limit):
            break
    print("found {n} study properties".format(n=len(study_key_set)))
    for k in study_key_set:
        print(k)
    print("found {n} tree properties".format(n=len(tree_key_set)))
    for k in tree_key_set:
        print(k)
