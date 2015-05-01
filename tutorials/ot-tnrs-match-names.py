#!/usr/bin/env python
'''Simple command-line tool that wraps the taxonomic name matching service
    which is described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#match_names
'''
import pprint
import sys

def ot_tnrs_match_names(name_list,
                        context_name=None,
                        do_approximate_matching=True,
                        include_dubious=False,
                        include_deprecated=True,
                        tnrs_wrapper=None):
    '''Uses a peyotl wrapper around an Open Tree web service to get a list of OTT IDs matching
    the `name_list`.
    The tnrs_wrapper can be None (in which case the default wrapper from peyotl.sugar will be used.
    All other arguments correspond to the arguments of the web-service call.
    A ValueError will be raised if the `context_name` does not match one of the valid names for a
        taxonomic context.
    This uses the wrap_response option to create and return a TNRSRespose object around the response.
    '''
    if tnrs_wrapper is None:
        from peyotl.sugar import tnrs
        tnrs_wrapper = tnrs
    match_obj = tnrs_wrapper.match_names(name_list,
                                         context_name=context_name,
                                         do_approximate_matching=do_approximate_matching,
                                         include_deprecated=include_deprecated,
                                         include_dubious=include_dubious,
                                         wrap_response=True)
    return match_obj


def match_and_print(name_list, context_name, do_approximate_matching, include_dubious, include_deprecated, output):
    '''Demonstrates how to read the response from a match_names query when peyotl's wrap_response option is
    used.

    If the context_name is not recognized, the attempt to match_names will generate a ValueError exception.
    Here this is caught, and we call the tnrs/contexts web service to get the list of valid context_names
        to provide the user of the script with some hints.
    '''
    from peyotl.sugar import tnrs
    try:
        # Perform the match_names, and return the peyotl wrapper around the response.
        result = ot_tnrs_match_names(name_list,
                                     context_name=context_name,
                                     do_approximate_matching=do_approximate_matching,
                                     include_dubious=include_dubious,
                                     include_deprecated=include_deprecated,
                                     tnrs_wrapper=tnrs)
    except Exception as x:
        msg = str(x)
        if 'is not a valid context name' in msg and context_name is not None:
            # Here is a wrapper around the call to get the context names
            valid_contexts = tnrs.contexts()
            m = 'The valid context names are the strings in the values of the following "tnrs/contexts" dict:\n'
            sys.stderr.write(m)
            epp = pprint.PrettyPrinter(indent=4, stream=sys.stderr)
            epp.pprint(valid_contexts)
        raise RuntimeError('ot-tnrs-match-names: exception raised. {}'.format(x))
    # The code below demonstrates how to access the information from the response in the wrapper
    #   that is created by using the wrap_response option in the call
    output.write(u'A v2/tnrs/match_names query was performed using: {} \n'.format(tnrs.endpoint))
    output.write(u'The taxonomy being served by that server is:')
    output.write(u' {}'.format(result.taxonomy.source))
    output.write(u' by {}\n'.format(result.taxonomy.author))
    output.write(u'Information for the taxonomy can be found at {}\n'.format(result.taxonomy.weburl))
    output.write(u'{} out of {} queried name(s) were matched\n'.format(len(result.matched_name_ids), len(name_list)))
    output.write(u'{} out of {} queried name(s) were unambiguously matched\n'.format(len(result.unambiguous_name_ids), len(name_list)))
    output.write(u'The context_name for the matched names was "{}"'.format(result.context))
    if result.context_inferred:
        output.write(u' (this context was inferred based on the matches).\n')
    else:
        output.write(u' (this context was supplied as an argument to speed up the name matching).\n')
    output.write(u'The name matching result(s) used approximate/fuzzy string matching? {}\n'.format(result.includes_approximate_matches))
    output.write(u'The name matching result(s) included dubious names? {}\n'.format(result.includes_dubious_names))
    output.write(u'The name matching result(s) included deprecated taxa? {}\n'.format(result.includes_deprecated_taxa))
    for name in name_list:
        match_tuple = result[name]
        output.write(u'The query name "{}" produced {} result(s):\n'.format(name, len(match_tuple)))
        for match_ind, match in enumerate(match_tuple):
            output.write(u'  Match #{}\n'.format(match_ind))
            output.write(u'    OTT ID (ot:ottId) = {}\n'.format(match.ott_id))
            output.write(u'    name (ot:ottTaxonName) = "{}"\n'.format(match.name))
            output.write(u'    query was matched using fuzzy/approximate string matching? {}\n'.format(match.is_approximate_match))
            output.write(u'    match score = {}\n'.format(match.score))
            output.write(u'    query name is a junior synonym of this match? {}\n'.format(match.is_synonym))
            output.write(u'    is deprecated from OTT? {}\n'.format(match.is_deprecated))
            output.write(u'    is dubious taxon? {}\n'.format(match.is_dubious))
            if match.synonyms:
                output.write(u'    known synonyms: "{}"\n'.format('", "'.join(match.synonyms)))
            else:
                output.write(u'    known synonyms: \n')
            output.write(u'    OTT flags for this taxon: {}\n'.format(match.flags))
            output.write(u'    The taxonomic rank associated with this name is: {}\n'.format(match.rank))
            output.write(u'    The nomenclatural code for this name is: {}\n'.format(match.nomenclature_code))
            output.write(u'    The (unstable) node ID in the current taxomachine instance is: {}\n'.format(match.taxomachine_node_id))

def main(argv):
    '''This function sets up a command-line option parser and then calls match_and_print
    to do all of the real work.
    '''
    import argparse
    import codecs
    description = 'Uses Open Tree of Life web services to try to find a taxon ID for each name supplied. ' \
                  'Using a --context-name=NAME to provide a limited taxonomic context and using the '\
                  ' --prohibit-fuzzy-matching option can make the matching faster.'
    parser = argparse.ArgumentParser(prog='ot-tnrs-match-names', description=description)
    parser.add_argument('names', nargs='+', help='name(s) for which we will try to find OTT IDs')
    parser.add_argument('--context-name', default=None, type=str, required=False)
    parser.add_argument('--include-dubious',
                        action='store_true',
                        default=False,
                        required=False,
                        help='return matches to taxa that are not included the synthetic tree because their taxonomic status is doubtful')
    parser.add_argument('--include-deprecated', action='store_true', default=False, required=False)
    parser.add_argument('--prohibit-fuzzy-matching', action='store_true', default=False, required=False)
    args = parser.parse_args(argv)
    # The service takes do_approximate_matching
    # We use the opposite to make the command-line just include positive directives
    #   (as opposed to requiring --do-approximate-matching=False) so we use "not"
    do_approximate_matching = not args.prohibit_fuzzy_matching
    name_list = args.names
    if len(name_list) == 0:
        name_list = ["Homo sapiens", "Gorilla gorilla"]
        sys.stderr.write('Running a demonstration query with {}\n'.format(name_list))
    else:
        for name in name_list:
            if name.startswith('-'):
                parser.print_help()
    # have to be ready to deal with utf-8 names
    out = codecs.getwriter('utf-8')(sys.stdout)
    match_and_print(name_list,
                    context_name=args.context_name,
                    do_approximate_matching=do_approximate_matching,
                    include_dubious=args.include_dubious,
                    include_deprecated=args.include_deprecated,
                    output=out)
if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        sys.exit('{}\n'.format(str(x)))

