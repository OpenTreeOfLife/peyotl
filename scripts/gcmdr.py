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
    GCMDR_CONFIG_FILE higher priority than PEYOTL_CONFIG, but lower than
        command-line options
'''
    commands = ['taxonomy', 'fetchNexsons', 'loadGraph', 'synthesize', 'extractSynthesis']
    lc_commands = [i.lower() for i in commands]
    requires_studies = ['fetchnexsons', 'loadgraph']
    parser = argparse.ArgumentParser(description=_HELP_MESSAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=_EPILOG)
    parser.add_argument("command",
                        help='a command from: {}'.format(' '.join(commands)))
    parser.add_argument("--reinitialize",
                        action='store_true',
                        help='if used, with the loadGraph command, the studies database will'\
                        'be removed and repopulated with just the taxonomy before studies are loaded')
    parser.add_argument("--download",
                        action='store_true',
                        help='if used, with the fetchNexsons command, the git repo will be refreshed with a pull '\
                        'the NexSONs are transformed into th form treemachine needs. Without this option, the '\
                        'studies will be fetched from your local phyleystem repo, but that repo will not be touched.')
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
                        'specified by the GCMDR_CONFIG_FILE env var (if used).')
    args = parser.parse_args()
    cmd = args.command.lower()
    if cmd not in lc_commands:
        sys.exit('Expecting the command to be one of: {}'.format(', '.join(commands)))
    cfg_filepaths = [None] # always read the default peyotl config
    ecfg = os.environ.get('GCMDR_CONFIG_FILE')
    if ecfg is not None:
        cfg_filepaths.append(ecfg)
    if args.config:
        cfg_filepaths.append(args.config)
    cfg, read_cfg_files = read_config(cfg_filepaths)
    _LOG.debug('read configuration in lowest->highest priority from: "{}"'.format('", "'.join(read_cfg_files)))
    if cmd in requires_studies:
        if args.studies is None:
            sys.exit('A list of trees in studies (--studies arg) must be specified when using the "{}" command'.format(cmd))
        tree_list = parse_study_tree_list(args.studies)
    gcmdr = GraphCommander(config=cfg, read_config_files=read_cfg_files)
    if cmd == 'taxonomy':
        gcmdr.load_taxonomy()
    elif cmd == 'fetchnexsons':
        gcmdr.fetch_nexsons(tree_list, download=args.download)
    elif cmd == 'loadgraph':
        gcmdr.load_graph(tree_list, reinitialize=args.reinitialize)
    elif cmd == 'synthesize':
        gcmdr.synthesize()
    elif cmd == 'extractsynthesis':
        print gcmdr.extract_synthesis()
