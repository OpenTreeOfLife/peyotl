#!/usr/bin/env python
import sys
from peyotl.nexson_validation import NexsonError, \
                                     NexsonWarningCodes, \
                                     validate_nexson
SCRIPT_NAME = __name__  #@TODO replace with logger...
ERR_STREAM = sys.stderr #@TODO replace with logger...

def error(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: ERROR: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def warn(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: WARNING: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def info(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

if __name__ == '__main__':
    import json
    import os
    import codecs
    import argparse
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

    parser = argparse.ArgumentParser(description='Validate a json file as Open Tree of Life NexSON')
    parser.add_argument('--verbose', dest='verbose', action='store_true', default=False, help='verbose output')
    parser.add_argument('--meta', dest='meta', action='store_true', default=False, help='warn about unvalidated meta elements')
    parser.add_argument('input', metavar='filepath', type=unicode, nargs=1, help='filename')
    args = parser.parse_args()
    SCRIPT_NAME = os.path.split(sys.argv[0])[-1]
    try:
        inp_filepath = args.input[0]
    except:
        sys.exit('Expecting a filepath to a NexSON file as the only argument.\n')
    inp = codecs.open(inp_filepath, 'rU', encoding='utf-8')
    try:
        obj = json.load(inp)
    except ValueError as vx:
        error('Not valid JSON.')
        if args.verbose:
            raise vx
        else:
            sys.exit(1)
    codes_to_skip = None
    if not args.meta:
        codes_to_skip = [NexsonWarningCodes.UNVALIDATED_ANNOTATION]
    try:
        v, n = validate_nexson(obj, codes_to_skip)
    except NexsonError as nx:
        error(nx.value)
        sys.exit(1)
    if (not v.errors) and (not v.warnings):
        info('Valid')
    elif v.errors:
        for el in v.errors:
            error(el)
    else:
        for el in v.warnings:
            warn(el)
