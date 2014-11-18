#!/usr/bin/env python
from peyotl.utility import get_logger, ConfigWrapper
import os
_LOG = get_logger('peyotl')

def parse_config_file(fp):
    try:
        from ConfigParser import SafeConfigParser
    except ImportError:
        from configparser import ConfigParser as SafeConfigParser
    if not os.path.exists(fp):
        raise RuntimeError('The config filepath "{fp}" does not exist.'.format(fp=fp))
    config_obj = SafeConfigParser()
    config_obj.read(fp)
    return config_obj

def config_command(args):
    out = sys.stdout
    if args.action.lower() == 'list':
        fp = args.filepath
        if fp:
            fp = os.path.abspath(fp)
            cfg = parse_config_file(fp)
            cw = ConfigWrapper(raw_config_obj=cfg, config_filename=fp)
        else:
            cw = ConfigWrapper()
        cw.report(out)
            

if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(prog='peyotl')
    subparsers = parser.add_subparsers(help='available commands')
    parser_config = subparsers.add_parser('config', help='reports information about your peyotl configuration')
    parser_config.add_argument('-a', '--action', choices=['list'], default='list', required=False)
    parser_config.add_argument('-f', '--filepath', type=str, default=None, required=False)
    parser_config.set_defaults(func=config_command)
    args = parser.parse_args(sys.argv[1:])
    try:
        args.func(args)
    except:
        _LOG.exception('peyotl.py terminating due to an exception')
        sys.exit(1)


