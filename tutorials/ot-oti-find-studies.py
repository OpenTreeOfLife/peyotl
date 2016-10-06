#!/usr/bin/env python
from __future__ import print_function

'''Simple command-line tool that wraps OTI to get studies for an argument which is a property value pair
   e.g. python ot-oti-find-studies.py '{"ot:studyId": "ot_308"}'
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#find_studies
'''
import sys
import json


def ot_find_studies(arg_dict, exact=True, verbose=False, oti_wrapper=None):
    """Uses a peyotl wrapper around an Open Tree web service to get a list of studies
    including values `value` for a given property to be searched on `porperty`.

    The oti_wrapper can be None (in which case the default wrapper from peyotl.sugar will be used.
    All other arguments correspond to the arguments of the web-service call.
    """
    if oti_wrapper is None:
        from peyotl.sugar import oti
        oti_wrapper = oti
    return oti_wrapper.find_studies(arg_dict,
                                    exact=exact,
                                    verbose=verbose,
                                    wrap_response=True)


def print_matching_studies(arg_dict, exact, verbose):
    """ """
    from peyotl.sugar import phylesystem_api
    study_list = ot_find_studies(arg_dict, exact=exact, verbose=verbose)
    for study in study_list:
        print(study)


def main(argv):
    """This function sets up a command-line option parser and then calls print_matching_trees
    to do all of the real work.
    """
    import argparse
    description = 'Uses Open Tree of Life web services to try to find a tree with the value property pair specified. ' \
                  'setting --fuzzy will allow fuzzy matching'
    parser = argparse.ArgumentParser(prog='ot-get-tree', description=description)
    parser.add_argument('arg_dict', type=json.loads, help='name(s) for which we will try to find OTT IDs')
    parser.add_argument('--property', default=None, type=str, required=False)
    parser.add_argument('--fuzzy', action='store_true', default=False,
                        required=False)  # exact matching and verbose not working atm...
    parser.add_argument('--verbose', action='store_true', default=False, required=False)
    try:
        args = parser.parse_args(argv)
        arg_dict = args.arg_dict
        exact = not args.fuzzy
        verbose = args.verbose
    except:
        arg_dict = {'ot:studyId': 'ot_308'}
        sys.stderr.write('Running a demonstration query with {}\n'.format(arg_dict))
        exact = True
        verbose = False
    print_matching_studies(arg_dict, exact=exact, verbose=verbose)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as x:
        sys.exit('{}\n'.format(str(x)))
