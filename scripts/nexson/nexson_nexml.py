from peyotl.nexson_syntax import write_obj_as_nexml, \
                                 get_ot_study_info_from_nexml, \
                                 BADGER_FISH_NEXSON_VERSION, \
                                 DEFAULT_NEXSON_VERSION
#secret#hacky#cut#paste*nexson_nexml.py##################################

def _main():
    import sys, codecs, json, os
    import argparse
    from cStringIO import StringIO
    _HELP_MESSAGE = '''NeXML/NexSON converter'''
    _EPILOG = '''UTF-8 encoding is used (for input and output).

Environmental variables used:
    NEXSON_INDENTATION_SETTING indentation in NexSON (default 0)
    NEXML_INDENTATION_SETTING indentation in NeXML (default is 0).
    NEXSON_LOGGING_LEVEL logging setting: NotSet, Debug, Warn, Info, Error
    NEXSON_LOGGING_FORMAT format string for logging messages.
'''
    parser = argparse.ArgumentParser(description=_HELP_MESSAGE,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=_EPILOG)
    parser.add_argument("input", help="filepath to input")
    parser.add_argument("-o", "--output", 
                        metavar="FILE",
                        required=False,
                        help="output filepath. Standard output is used if omitted.")
    codes = 'xjb'
    parser.add_argument("-m", "--mode", 
                        metavar="MODE",
                        required=False,
                        choices=[i + j for i in codes for j in codes],
                        help="Two letter code for {input}{output} \
                               The letters are x for NeXML, j for NexSON, \
                               and b for BadgerFish JSON version of NexML. \
                               The default behavior is to autodetect the format \
                               and convert JSON to NeXML or NeXML to NexSON.")
    args = parser.parse_args()
    inpfn = args.input
    outfn = args.output
    mode = args.mode
    try:
        inp = codecs.open(inpfn, mode='rU', encoding='utf-8')
    except:
        sys.exit('nexson_nexml: Could not open file "{fn}"\n'.format(fn=inpfn))
    if mode is None:
        try:
            while True:
                first_graph_char = inp.read(1).strip()
                if first_graph_char == '<':
                    mode = 'xj'
                    break
                elif first_graph_char in '{[':
                    mode = '*x'
                    break
                elif first_graph_char:
                    raise ValueError('Expecting input to start with <, {, or [')
        except:
            sys.exit('nexson_nexml: First character of "{fn}" was not <, {, or [\nInput does not appear to be NeXML or NexSON\n'.format(fn=inpfn))
        inp.seek(0)
    
    if mode.endswith('j'):
        indentation = int(os.environ.get('NEXSON_INDENTATION_SETTING', 0))
    else:
        indentation = int(os.environ.get('NEXML_INDENTATION_SETTING', 0))
    
    if outfn is not None:
        try:
            out = codecs.open(outfn, mode='w', encoding='utf-8')
        except:
            sys.exit('nexson_nexml: Could not open output filepath "{fn}"\n'.format(fn=outfn))
    else:
        out = codecs.getwriter('utf-8')(sys.stdout)

    if mode.endswith('b'):
        out_nexson_format = BADGER_FISH_NEXSON_VERSION
    else:
        out_nexson_format = DEFAULT_NEXSON_VERSION
    if mode.startswith('x'):
        blob = get_ot_study_info_from_nexml(inp,
                                            nexson_syntax_version=out_nexson_format)
    else:
        blob = json.load(inp)
        if mode.startswith('*'):
            n = blob.get('nex:nexml') or blob.get('nexml')
            if not n or (not isinstance(n, dict)):
                sys.exit('No top level "nex:nexml" element found. Document does not appear to be a JSON version of NeXML\n')
            if n:
                v = n.get('@nexml2json', '0.0.0')
                if v.startswith('0'):
                    mode = 'b' + mode[1]
                else:
                    mode = 'j' + mode[1]

    if mode.endswith('x'):
        syntax_version = BADGER_FISH_NEXSON_VERSION
        if mode.startswith('j'):
            syntax_version = NEXSON_VERSION
        if indentation > 0:
            indent = ' '*indentation
        else:
            indent = ''
        newline = '\n'
        write_obj_as_nexml(blob,
                           out,
                           addindent=indent,
                           newl=newline,
                           nexson_syntax_version=syntax_version)
    else:
        if not mode.startswith('x'):
            xo = StringIO()
            write_obj_as_nexml(blob,
                           xo,
                           addindent=' ',
                           newl='\n',
                           nexson_syntax_version=out_nexson_format)
            xml_content = xo.getvalue()
            xi = StringIO(xml_content)
            blob = get_ot_study_info_from_nexml(xi,
                    nexson_syntax_version=out_nexson_format)
        json.dump(blob, out, indent=indentation, sort_keys=True)
        out.write('\n')

if __name__ == '__main__':
    _main()
