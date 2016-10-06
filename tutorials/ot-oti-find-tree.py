#!/usr/bin/env python
from __future__ import print_function

'''Simple command-line tool that wraps OTI to get trees for an argument which is a property value pair
   e.g. python ot-oti-find-tree.py '{"ot:ottTaxonName": "Bos"}'
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#find_trees
'''
import sys
import json

def ot_find_tree(arg_dict, exact=True,  verbose=False, oti_wrapper=None):
    '''Uses a peyotl wrapper around an Open Tree web service to get a list of trees including values `value` for a given property to be searched on `porperty`.

    The oti_wrapper can be None (in which case the default wrapper from peyotl.sugar will be used.
    All other arguments correspond to the arguments of the web-service call.
    '''
    if oti_wrapper is None:
        from peyotl.sugar import oti
        oti_wrapper = oti
    return oti_wrapper.find_trees(arg_dict,
                                  exact=exact,
                                  verbose=verbose,
                                  wrap_response=True)

def print_matching_trees(arg_dict, tree_format, exact, verbose):
    '''The `TreeRef` instance returned by the oti.find_trees(... wrap_response=True)
    can be used as an argument to the phylesystem_api.get call.
    If you pass in a string (instead of a TreeRef), the string will be interpreted as a study ID
    '''
    from peyotl.sugar import phylesystem_api
    tree_list = ot_find_tree(arg_dict, exact=exact, verbose=verbose)
    for tree_ref in tree_list:
        print(tree_ref)
        print(phylesystem_api.get(tree_ref, format=tree_format))

def main(argv):
    '''This function sets up a command-line option parser and then calls print_matching_trees
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
        verbose = args.verbose
        tree_format = args.format.lower()
    except:
        arg_dict = {'ot:ottTaxonName':'Chamaedorea frondosa'}
        sys.stderr.write('Running a demonstration query with {}\n'.format(arg_dict))
        exact = True
        verbose = False
        tree_format = 'newick'
    if tree_format not in ('newick', 'nexson', 'nexml', 'nexus'):
        raise ValueError('Unrecognized format "{}"'.format(tree_format))
    print_matching_trees(arg_dict, tree_format, exact=exact, verbose=verbose)

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as x:
        sys.exit('{}\n'.format(str(x)))

