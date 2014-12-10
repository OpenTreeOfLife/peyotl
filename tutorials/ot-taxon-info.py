#!/usr/bin/env python
'''Simple command-line tool for reporting information about an ott ID using the taxonomy/taxon web service
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#taxon
'''
import sys

def fetch_and_write_taxon_info(id_list, include_anc, output):
    from peyotl.sugar import taxonomy
    for ott_id in id_list:
        info = taxonomy.taxon(ott_id, include_lineage=include_anc, wrap_response=True)
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
    output.write('Taxon info for OTT ID (ot:ottId) = {}\n'.format(taxon.ott_id))
    output.write('    name (ot:ottTaxonName) = "{}"\n'.format(taxon.name))
    #output.write('    taxon is a junior synonym ? {}\n'.format(match.is_synonym))
    #output.write('    is deprecated form OTT? {}\n'.format(match.is_deprecated))
    #output.write('    is dubious taxon? {}\n'.format(match.is_dubious))
    if taxon.synonyms:
        output.write('    known synonyms: "{}"\n'.format('", "'.join(taxon.synonyms)))
    else:
        output.write('    known synonyms: \n')
    output.write('    OTT flags for this taxon: {}\n'.format(taxon.flags))
    output.write('    The taxonomic rank associated with this name is: {}\n'.format(taxon.rank))
    #output.write('    The nomenclatural code for this name is: {}\n'.format(taxon.nomenclature_code))
    output.write('    The (unstable) node ID in the current taxomachine instance is: {}\n'.format(taxon.taxomachine_node_id))
    if include_anc:
        if taxon.parent is not None:
            output.write('Taxon {c} is a child of {p}.\n'.format(c=taxon.ott_id, p=taxon.parent.ott_id))
            write_taxon_info(taxon.parent, True, output)
        else:
            output.write('Taxon {c} is the root of the taxonomy.'.format(c=taxon.ott_id))


def main(argv):
    '''This function sets up a command-line option parser and then calls match_and_print
    to do all of the real work.
    '''
    import argparse
    description = 'Uses Open Tree of Life web services to find information for each OTT ID.'
    parser = argparse.ArgumentParser(prog='ot-taxon-info', description=description)
    parser.add_argument('ids', nargs='*', type=int, help='OTT IDs')
    parser.add_argument('--include-lineage', action='store_true', default=False, required=False,
                        help='list the IDs of the ancestors as well.')
    args = parser.parse_args(argv)
    id_list = args.ids
    fetch_and_write_taxon_info(id_list, args.include_lineage, sys.stdout)
    
if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        raise
        sys.exit('{}\n'.format(str(x)))

