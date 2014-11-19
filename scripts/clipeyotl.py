#!/usr/bin/env python
from peyotl.utility import get_logger, ConfigWrapper
import sys
import os
_LOG = get_logger('clipeyotl')
out = sys.stdout

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
    if args.action.lower() == 'list':
        fp = args.filepath
        if fp:
            fp = os.path.abspath(fp)
            cfg = parse_config_file(fp)
            cw = ConfigWrapper(raw_config_obj=cfg, config_filename=fp)
        else:
            cw = ConfigWrapper()
        cw.report(out)
def ott_clear_command(args):
    from peyotl.ott import OTT
    ott = OTT()
    ott.remove_caches()

def main():
    import argparse
    parser = argparse.ArgumentParser(prog='cli-peyotl.py')
    subparsers = parser.add_subparsers(help='available commands')
    # config commands
    config_parser = subparsers.add_parser('config', help='reports information about your peyotl configuration')
    config_parser.add_argument('-a', '--action', choices=['list'], default='list', required=False)
    config_parser.add_argument('-f', '--filepath', type=str, default=None, required=False)
    config_parser.set_defaults(func=config_command)
    # ott commands
    ott_parser = subparsers.add_parser('ott', help='commands that require a local version of ott')
    #ott_parser.add_argument('--action', choices=['clear-cache'], default='', required=False)
    ott_subparsers = ott_parser.add_subparsers(help='ott actions')
    ott_clear_parser = ott_subparsers.add_parser('clear-cache',
                                                 help='remove the caches used to speed up actions on OTT')
    ott_clear_parser.set_defaults(func=ott_clear_command)

    args = parser.parse_args(sys.argv[1:])
    try:
        args.func(args)
    except:
        _LOG.exception('peyotl.py terminating due to an exception')
        sys.exit(1)


if __name__ == '__main__':
    main()
