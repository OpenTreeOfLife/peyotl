#!/usr/bin/env python
'''Simple command-line tool for reporting information a subtree of the OTT reference taxonomy using
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#subtree
'''
import sys

def fetch_and_write_taxon_subtree(ott_id, output):
    from peyotl.sugar import taxonomy
    subtree = taxonomy.subtree(ott_id)['subtree']
    output.write(subtree)
    output.write('\n')


def main(argv):
    '''This function sets up a command-line option parser and then calls match_and_print
    to do all of the real work.
    '''
    import argparse
    description = 'Uses Open Tree of Life web services to find information for each OTT ID.'
    parser = argparse.ArgumentParser(prog='ot-taxon-info', description=description)
    parser.add_argument('ids', nargs='+', type=int, help='OTT IDs')
    args = parser.parse_args(argv)
    id_list = args.ids
    for ott_id in id_list:
        fetch_and_write_taxon_subtree(ott_id, sys.stdout)
    
if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        sys.exit('{}\n'.format(str(x)))

