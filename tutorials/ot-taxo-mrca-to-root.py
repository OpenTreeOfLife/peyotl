#!/usr/bin/env python
'''Takes a series of at least 2 OTT ids and reports the OTT of their
least inclusive taxonomic ancestor and that taxon's ancestors.
'''

import sys

def get_taxonomic_ancestor_ids(ott_id):
    from peyotl.sugar import taxonomy
    info = taxonomy.taxon(ott_id,
                          include_lineage=True,
                          list_terminal_descendants=False,
                          wrap_response=True)
    anc_id_list = []
    while True:
        anc_id_list.append(info.ott_id)
        info = info.parent
        if info is None:
            return anc_id_list


def main(argv):
    '''This function sets up a command-line option parser and then calls 
    to do all of the real work.
    '''
    import argparse
    import codecs
    # have to be ready to deal with utf-8 names
    out = codecs.getwriter('utf-8')(sys.stdout)
    description = '''Takes a series of at least 2 OTT ids and reports the OTT of their least inclusive taxonomic ancestor and that taxon's ancestors.'''
    parser = argparse.ArgumentParser(prog='ot-taxo-mrca-to-root', description=description)
    parser.add_argument('ids', nargs='+', type=int, help='OTT IDs')
    args = parser.parse_args(argv)
    id_list = args.ids
    last_id = id_list.pop()
    anc_list = get_taxonomic_ancestor_ids(last_id)
    common_anc = set(anc_list)
    for curr_id in id_list:
        curr_anc_set = set(get_taxonomic_ancestor_ids(curr_id))
        common_anc &= curr_anc_set
        if not common_anc:
            break
    for anc_id in anc_list:
        if anc_id in common_anc:
            out.write('{}\n'.format(anc_id))

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        sys.exit('{}\n'.format(str(x)))

