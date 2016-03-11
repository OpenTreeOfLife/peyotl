#!/usr/bin/env python
from peyotl import collection_to_included_trees, read_as_json

if __name__ == '__main__':
    import argparse
    import codecs
    import sys
    import os
    description = 'Takes an collection JSON and prints out information from it'
    parser = argparse.ArgumentParser(prog='collection_export.py', description=description)
    parser.add_argument('--export',
                        default='studyID_treeID',
                        type=str,
                        required=False,
                        choices=('studyID_treeID', 'studyID'))
    parser.add_argument('collection',
                        default=None,
                        type=str,
                        help='filepath for the collections JSON')
    args = parser.parse_args(sys.argv[1:])
    export = args.export
    if not os.path.isfile(args.collection):
        sys.exit('Input collection "{}" does not exist.\n'.format(args.collection))
    try:
        included = collection_to_included_trees(args.collection)
    except:
        sys.stderr.write('JSON parse error when reading collection "{}".\n'.format(args.collection))
        raise
    for d in included:
        if export == 'studyID_treeID':
            print '@'.join([d['studyID'], d['treeID']])
        else:
            assert export == 'studyID'
            print d['studyID']
