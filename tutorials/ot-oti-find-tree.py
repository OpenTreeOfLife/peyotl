#!/usr/bin/env python
'''Simple command-line tool that wraps the OTI to get trees for a taxon ID
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#match_names
'''
import pprint
import sys
import json

def ot_find_tree(pair, exact=True,  verbose=True, oti_wrapper=None):
                        
    '''Uses a peyotl wrapper around an Open Tree web service to get a list of trees including values `value` for a given property to be searched on `porperty`.

    The oti_wrapper can be None (in which case the default wrapper from peyotl.sugar will be used.
    All other arguments correspond to the arguments of the web-service call.
    '''
    if oti_wrapper is None:
        from peyotl.sugar import oti
        oti_wrapper = oti

    match_obj = oti_wrapper.find_trees(pair)
    return match_obj

def main(argv):
    '''This function sets up a command-line option parser and then calls match_and_print
    to do all of the real work.
    '''
    import argparse
    description = 'Uses Open Tree of Life web services to try to find a tree with the value property pair specified. ' \
                  'setting --exact-match to false will allow fuzzy matching'

    parser = argparse.ArgumentParser(prog='ot-get-tree', description=description)
    parser.add_argument('arg_dict', type=json.loads, help='name(s) for which we will try to find OTT IDs')
    parser.add_argument('--property', default=None, type=str, required=False)
#    parser.add_argument('--fuzzy', action='store_true', default=False, required=False)
    parser.add_argument('--verbose', action='store_true', default=True, required=False)
    
    args = parser.parse_args(argv)
    arg_dict = args.arg_dict
    print(arg_dict)
    if len(arg_dict) == 0:
        arg_dict = {"ot:ottTaxonName":"Garcinia"}
        sys.stderr.write('Running a demonstration query with {}\n'.format(arg_dict))
    print(ot_find_tree(arg_dict))
if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        sys.exit('{}\n'.format(str(x)))

