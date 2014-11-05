#!/usr/bin/env python
from peyotl.nexson_syntax import create_content_spec, \
                                 get_ot_study_info_from_nexml, \
                                 PhyloSchema

def _main():
    import sys, codecs, json
    import argparse
    _HELP_MESSAGE = '''NexSON (or NeXML) to newick converter'''
    _EPILOG = '''UTF-8 encoding is used (for input and output).

Environmental variables used:
    NEXSON_LOGGING_LEVEL logging setting: NotSet, Debug, Warn, Info, Error
    NEXSON_LOGGING_FORMAT format string for logging messages.
'''
    tip_label_list = PhyloSchema._otu_label_list
    for tl in tip_label_list:
        assert(tl.startswith('ot:'))
    tip_labels_choices = [i[3:] for i in tip_label_list]
    parser = argparse.ArgumentParser(description=_HELP_MESSAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=_EPILOG)
    parser.add_argument("input", help="filepath to input")
    parser.add_argument("-i", "--id",
                        metavar="TREE-ID",
                        required=False,
                        help="The ID tree to emit")
    parser.add_argument("-o", "--output",
                        metavar="FILE",
                        required=False,
                        help="output filepath. Standard output is used if omitted.")
    parser.add_argument("-l", "--list",
                        action="store_true",
                        default=False,
                        help="Just list the tree IDs in the nexSON.")
    parser.add_argument("-x", "--xml",
                        action="store_true",
                        default=False,
                        help="Parse input as NeXML rather than NexSON.")
    tl_help = 'The field to use to label tips. Should be one of: "{}"'
    tl_help = tl_help.format('", "'.join(tip_labels_choices))
    parser.add_argument("-t", "--tip-label",
                        metavar="STRING",
                        required=False,
                        default='originallabel',
                        help=tl_help)
    args = parser.parse_args()
    otu_label = args.tip_label.lower()
    if not otu_label.startswith('ot:'):
        otu_label = 'ot:' + otu_label
    if otu_label not in tip_label_list:
        sys.exit('Illegal tip label choice "{}"\n'.format(args.tip_label))

    inpfn = args.input
    outfn = args.output
    try:
        inp = codecs.open(inpfn, mode='rU', encoding='utf-8')
    except:
        sys.exit('nexson_newick: Could not open file "{fn}"\n'.format(fn=inpfn))

    if outfn is not None:
        try:
            out = codecs.open(outfn, mode='w', encoding='utf-8')
        except:
            sys.exit('nexson_newick: Could not open output filepath "{fn}"\n'.format(fn=outfn))
    else:
        out = codecs.getwriter('utf-8')(sys.stdout)
    
    if args.xml:
        src_schema = PhyloSchema('nexml')
        blob = get_ot_study_info_from_nexml(inp)
    else:
        src_schema = None
        blob = json.load(inp)
    if args.list:
        schema = PhyloSchema(content='treelist', output_nexml2json='1.2.1')
        tl = schema.convert(src=blob, src_schema=src_schema)
        out.write('{t}\n'.format(t='\n'.join(tl)))
    else:
        schema = create_content_spec(content='tree', content_id=args.id, format='newick', otu_label=otu_label)
        schema.convert(src=blob, serialize=True, output_dest=out, src_schema=src_schema)

if __name__ == '__main__':
    _main()
