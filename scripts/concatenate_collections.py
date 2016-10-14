#!/usr/bin/env python
from peyotl import concatenate_collections, read_as_json, write_as_json

if __name__ == '__main__':
    import argparse
    import sys
    import os
    description = 'Takes a list of collections and writes a collection that is a concatenation of their decisions'
    parser = argparse.ArgumentParser(prog='collection_export.py', description=description)
    parser.add_argument('--output',
                        type=str,
                        required=True,
                        help='output filepath for collection json')
    parser.add_argument('collection',
                        default=None,
                        type=str,
                        nargs="*",
                        help='filepath for the collections JSON')
    args = parser.parse_args(sys.argv[1:])
    inp = [read_as_json(i) for i in args.collection]
    out = concatenate_collections(inp)
    write_as_json(out, args.output)
