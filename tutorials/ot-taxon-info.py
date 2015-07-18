#!/usr/bin/env python
'''Simple command-line tool for reporting information about an ott ID using the taxonomy/taxon web service
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#taxon
'''
import sys

def fetch_and_write_taxon_info(id_list, include_anc, list_tips, output):
    from peyotl.sugar import taxonomy
    for ott_id in id_list:
        info = taxonomy.taxon(ott_id,
                              include_lineage=include_anc,
                              list_terminal_descendants=list_tips,
                              wrap_response=True)
        write_taxon_info(info, include_anc, output)

def write_taxon_info(taxon, include_anc, output):
    '''Writes out data from `taxon` to the `output` stream to demonstrate
    the attributes of a taxon object. 
    (currently some lines are commented out until the web-services call returns more info. See:
        https://github.com/OpenTreeOfLife/taxomachine/issues/85
    ).
    If `include_anc` is True, then ancestor information was requested (so a None parent is only
        expected at the root of the tree)
    '''
    output.write(u'Taxon info for OTT ID (ot:ottId) = {}\n'.format(taxon.ott_id))
    output.write(u'    name (ot:ottTaxonName) = "{}"\n'.format(taxon.name))
    if taxon.synonyms:
        output.write(u'    known synonyms: "{}"\n'.format('", "'.join(taxon.synonyms)))
    else:
        output.write(u'    known synonyms: \n')
    output.write(u'    OTT flags for this taxon: {}\n'.format(taxon.flags))
    output.write(u'    The taxonomic rank associated with this name is: {}\n'.format(taxon.rank))
    output.write(u'    The (unstable) node ID in the current taxomachine instance is: {}\n'.format(taxon.taxomachine_node_id))
    if include_anc:
        if taxon.parent is not None:
            output.write(u'Taxon {c} is a child of {p}.\n'.format(c=taxon.ott_id, p=taxon.parent.ott_id))
            write_taxon_info(taxon.parent, True, output)
        else:
            output.write('uTaxon {c} is the root of the taxonomy.'.format(c=taxon.ott_id))


def main(argv):
    '''This function sets up a command-line option parser and then calls match_and_print
    to do all of the real work.
    '''
    import argparse
    import codecs
    # have to be ready to deal with utf-8 names
    out = codecs.getwriter('utf-8')(sys.stdout)
    
    description = 'Uses Open Tree of Life web services to find information for each OTT ID.'
    parser = argparse.ArgumentParser(prog='ot-taxon-info', description=description)
    parser.add_argument('ids', nargs='+', type=int, help='OTT IDs')
    parser.add_argument('--include-lineage', action='store_true', default=False, required=False,
                        help='list the IDs of the ancestors as well.')
    #uncomment when https://github.com/OpenTreeOfLife/taxomachine/issues/89 is fixed @TEMP
    #parser.add_argument('--list-tips', action='store_true', default=False, required=False,
    #                    help='list the tips in the subtree rooted by this taxon.')
    args = parser.parse_args(argv)
    id_list = args.ids
    list_tips = False # args.list_tips once https://github.com/OpenTreeOfLife/taxomachine/issues/89 is fixed @TEMP
    fetch_and_write_taxon_info(id_list, args.include_lineage, list_tips, out)
    
if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        sys.exit('{}\n'.format(str(x)))

