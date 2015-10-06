#!/usr/bin/env python
from peyotl.collections import get_empty_collection
from peyotl import collection_to_included_trees, read_as_json
from peyotl.phylesystem import Phylesystem
from collections import defaultdict
import codecs
import copy
import sys
import os

def copy_phylesystem_file_if_differing(git_action, coll_decision, out_dir, cd_to_new_map):
    study_id = coll_decision['studyID']
    fp = git_action.path_for_doc(study_id)
    print fp

if __name__ == '__main__':
    import argparse
    description = 'Takes an collection JSON and prints out information from it'
    parser = argparse.ArgumentParser(prog='suppress-dubious', description=description)
    parser.add_argument('--phylesystem-par',
                        default=None,
                        type=str,
                        required=False,
                        help='directory that holds the phylesystem shards (optional if you have peyotl configured)')
    parser.add_argument('collection',
                        default=None,
                        type=str,
                        help='filepath for the collections JSON')
    parser.add_argument('--output-dir',
                        default=None,
                        type=str,
                        required='False',
                        help='filepath for the output directory')
    args = parser.parse_args(sys.argv[1:])
    out_dir = '.' if args.output_dir is None else args.output_dir
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    # Create a Phylesystem wrapper
    if args.phylesystem_par is not None:
        if not os.path.isdir(args.phylesystem_par):
            sys.exit('Phylesystem parent "{}" is not a directory.\n'.format(args.phylesystem_par))
        ps = Phylesystem(repos_par=args.phylesystem_par)
    else:
        try:
            ps = Phylesystem()
        except:
            sys.stderr.write('Error: You need to use the --phylesystem-par argument, or a have a peyotl configuration that includes local phylesystem information.')
            raise
    # Get the list of included trees
    if not os.path.isfile(args.collection):
        sys.exit('Input collection "{}" does not exist.\n'.format(args.collection))
    try:
        included = collection_to_included_trees(args.collection)
    except:
        sys.stderr.write('Error: JSON parse error when reading collection "{}".\n'.format(args.collection))
        raise
    included_by_sha = defaultdict(list)
    for inc in included:
        included_by_sha[inc['SHA']].append(inc)
    # map id of input included tree to concrete form
    generic2concrete = {}
    use_latest_trees = included_by_sha['']
    if use_latest_trees:
        sha_to_inc = defaultdict(list)
        for ult in use_latest_trees:
            study_id = ult['studyID']
            ga = ps.create_git_action(study_id)
            sha = ga.get_master_sha()
            sha_to_inc[sha].append(ult)
        for sha, from_this_sha_inc in sha_to_inc.items():
            inc = from_this_sha_inc.pop(0)
            study_id = inc['studyID']
            ga = ps.create_git_action(study_id)
            ga.checkout_master()
            copy_phylesystem_file_if_differing(ga, inc, out_dir, generic2concrete)
            for inc in from_this_sha_inc:
                ga = ps.create_git_action(study_id)
                ga.checkout_master()
                copy_phylesystem_file_if_differing(ga, inc, out_dir, generic2concrete)
    for sha, from_this_sha_inc in included_by_sha.items():
        if sha == '':
            continue
        for inc in from_this_sha_inc:
            study_id = inc['studyID']
            ga = ps.create_git_action(study_id)
            ga.checkout(sha)
            copy_phylesystem_file_if_differing(ga, inc, out_dir, generic2concrete)
            ga.checkout_master()
    sys.exit()
    coll_name = os.path.split(args.collection)[-1]
    concrete_collection = get_empty_collection()
    concrete_collection['description'] = 'Concrete form of collection "{}"'.format(coll_name)
    cd_list = concrete_collection['decisions']
    for inc in included:
        concrete = generic2concrete[id(inc)]
        cd_list.append(concrete)
    concrete_fn = os.path.join(out_dir, 'concrete-' + coll_name)
    write_as_json(concrete_collection, concrete_fn)
