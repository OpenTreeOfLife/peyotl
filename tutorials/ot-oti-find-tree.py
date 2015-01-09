#!/usr/bin/env python
'''Simple command-line tool that wraps OTI to get trees for an argument which is a property value pair
   e.g. python ot-oti-find-tree.py '{"ot:ottTaxonName": "Bos"}' -n 2
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#find_trees
'''
import pprint
import sys
import json

def ot_find_tree(pair, exact=True,  verbose=False, oti_wrapper=None):
                        
    '''Uses a peyotl wrapper around an Open Tree web service to get a list of trees including values `value` for a given property to be searched on `porperty`.

    The oti_wrapper can be None (in which case the default wrapper from peyotl.sugar will be used.
    All other arguments correspond to the arguments of the web-service call.
    '''
    if oti_wrapper is None:
        from peyotl.sugar import oti
        oti_wrapper = oti
    return oti_wrapper.find_trees(pair, exact=exact, verbose=verbose, wrap_response=True)

def ot_get_tree(tree_ref, format='nexson'):
    from peyotl.api import APIWrapper
    api_wrapper = APIWrapper()
    return api_wrapper.study.get(tree_ref, format=format)

def main(argv):
    '''This function sets up a command-line option parser and then calls match_and_print
    to do all of the real work.
    '''
    import argparse
    description = 'Uses Open Tree of Life web services to try to find a tree with the value property pair specified. ' \
                  'setting --fuzzy will allow fuzzy matching'
    parser = argparse.ArgumentParser(prog='ot-get-tree', description=description)
    parser.add_argument('arg_dict', type=json.loads, help='name(s) for which we will try to find OTT IDs')
    parser.add_argument('--property', default=None, type=str, required=False)
    parser.add_argument('--fuzzy', action='store_true', default=False, required=False) #exact matching and verbose not working atm...
    parser.add_argument('--verbose', action='store_true', default=False, required=False)
    parser.add_argument('-f', '--format', type=str, default='newick', help='Format of the tree. Should be "newick", "nexson", "nexml", or "nexus"')
    try:
        args = parser.parse_args(argv)
        arg_dict = args.arg_dict
        exact = not args.fuzzy
        format = args.format.lower()
    except:
        arg_dict = {'ot:ottTaxonName':'Hedychium bordelonianum'}
        sys.stderr.write('Running a demonstration query with {}\n'.format(arg_dict))
        exact = True
        verbose = False
        format = 'newick'
    if format not in ('newick', 'nexson', 'nexml', 'nexus'):
        raise ValueError('Unrecognized format "{}"'.format(format))
    #print("arg dict is {}".format(arg_dict))
    from peyotl.sugar import phylesystem_api
    tree_list = ot_find_tree(arg_dict, exact=exact, verbose=verbose)
    for tree_ref in tree_list:
        print tree_ref
        print phylesystem_api.get(tree_ref, format=format)
        x = '''
        study_id = study['ot:studyId']
        for tree in study['matched_trees']:
            print(ot_get_tree(study_id, tree['oti_tree_id'], format=format))
            print('\n')
        '''


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        raise
        sys.exit('{}\n'.format(str(x)))

