#!/usr/bin/env python
if __name__ == '__main__':
    from peyotl import collection_to_included_trees, read_as_json
    from peyotl.phylesystem import Phylesystem
    import argparse
    import codecs
    import sys
    import os
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
    args = parser.parse_args(sys.argv[1:])
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
    print ps.get_configuration_dict()