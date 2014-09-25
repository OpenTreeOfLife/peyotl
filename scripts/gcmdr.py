#!/usr/bin/env python
from peyotl.utility import parse_study_tree_list
from peyotl.gcmdr import GraphCommander
from peyotl.utility import read_config
from peyotl import get_logger
_LOG = get_logger(__name__)

if __name__ == '__main__':
    import argparse
    import sys
    import os
    _HELP_MESSAGE = '''gcmdr - script to control treemachine syntheses'''
    _EPILOG = ''' Environmental variables used:
    PEYOTL_CONFIG_FILE (lowest priority settings)
    PEYOTL_LOGGING_LEVEL set to "debug" for more verbose output
    GCMR_CONFIG_FILE higher priority than PEYOTL_CONFIG, but lower than
        command-line options
'''
    commands = ['taxonomy', ]
    lc_commands = [i.lower() for i in commands]
    parser = argparse.ArgumentParser(description=_HELP_MESSAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=_EPILOG)
    parser.add_argument("command",
                        help='a command from: {}'.format(' '.join(commands)))
    parser.add_argument("--studies",
                        help='filepath to input JSON. Should contain an array of tree specifiers: '\
                        'either strings of the form pg_<#>_<treeid> or objects with "study_id" and '\
                        '"tree_id" properties. "git_sha" is an optional value for a study object, if '\
                        'omitted then it defaults to the most recent version of the study in the '\
                        'phyleystem repo.')
    parser.add_argument("-c", "--config",
                        metavar="FILE",
                        required=False,
                        help='config file (highest priority value of settings; this overrides the '\
                        'setting values found in the peyotl config and the values in the config '\
                        'specified by the GCMR_CONFIG_FILE env var (if used).')
    args = parser.parse_args()
    cmd = args.command.lower()
    if cmd not in lc_commands:
        sys.exit('Expecting the command to be one of: {}'.format(', '.join(commands)))
    cfg_filepaths = [None] # always read the default peyotl config
    ecfg = os.environ.get('GCMR_CONFIG_FILE')
    if ecfg is not None:
        cfg_filepaths.append(ecfg)
    if args.config:
        cfg_filepaths.append(args.config)
    cfg, read_cfg_files = read_config(cfg_filepaths)
    _LOG.debug('read configuration in lowest->highest priority from: "{}"'.format('", "'.join(read_cfg_files)))
    gcmdr = GraphCommander(cfg)
    if cmd == 'taxonomy':
        gcmdr.load_taxonomy()
