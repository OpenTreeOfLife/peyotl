#!/usr/bin/env python
from peyotl.nexson_syntax import convert_nexson_format, \
                                 get_nexson_version,\
                                 get_ot_study_info_from_nexml, \
                                 write_obj_as_nexml, \
                                 BADGER_FISH_NEXSON_VERSION, \
                                 DEFAULT_NEXSON_VERSION, \
                                 DIRECT_HONEY_BADGERFISH
#secret#hacky#cut#paste*nexson_nexml.py##################################

def _main():
    import sys, codecs, json, os
    import argparse
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
    parser.add_argument("-e", "--export", 
                        metavar="FMT",
                        required=False,
                        choices=["nexml",
                                 str(BADGER_FISH_NEXSON_VERSION),
                                 str(DIRECT_HONEY_BADGERFISH),
                                 "badgerfish"],
                        help="output format")
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
    export_format = args.export
    if export_format:
        if export_format.lower() ==  "badgerfish":
            export_format = str(BADGER_FISH_NEXSON_VERSION)
    if export_format is not None and mode is not None:
        if (mode.endswith('b') and (export_format != str(BADGER_FISH_NEXSON_VERSION))) \
           or (mode.endswith('x') and (export_format.lower() != "nexml")) \
           or (mode.endswith('x') and (export_format.lower() not in [str(DIRECT_HONEY_BADGERFISH)])):
            sys.exit('export format {e} clashes with mode {m}. The mode option is not neeeded if the export option is used.'.format(e=export_format, m=mode))
    try:
        inp = codecs.open(inpfn, mode='rU', encoding='utf-8')
    except:
        sys.exit('nexson_nexml: Could not open file "{fn}"\n'.format(fn=inpfn))
    if mode is None:
        try:
            while True:
                first_graph_char = inp.read(1).strip()
                if first_graph_char == '<':
                    mode = 'x*'
                    break
                elif first_graph_char in '{[':
                    mode = '*x'
                    break
                elif first_graph_char:
                    raise ValueError('Expecting input to start with <, {, or [')
        except:
            sys.exit('nexson_nexml: First character of "{fn}" was not <, {, or [\nInput does not appear to be NeXML or NexSON\n'.format(fn=inpfn))
        if export_format is None:
            if mode.endswith('*'):
                export_format = str(DIRECT_HONEY_BADGERFISH)
            else:
                export_format = "nexml"
        inp.seek(0)
    elif export_format is None:
        if mode.endswith('j'):
            export_format = str(DIRECT_HONEY_BADGERFISH)
        elif mode.endswith('b'):
            export_format = str(BADGER_FISH_NEXSON_VERSION)
        else:
            assert mode.endswith('x')
            export_format = "nexml"

    if export_format == "nexml":
        indentation = int(os.environ.get('NEXML_INDENTATION_SETTING', 0))
    else:
        indentation = int(os.environ.get('NEXSON_INDENTATION_SETTING', 0))
    
    if outfn is not None:
        try:
            out = codecs.open(outfn, mode='w', encoding='utf-8')
        except:
            sys.exit('nexson_nexml: Could not open output filepath "{fn}"\n'.format(fn=outfn))
    else:
        out = codecs.getwriter('utf-8')(sys.stdout)

    if mode.startswith('x'):
        blob = get_ot_study_info_from_nexml(inp,
                                            nexson_syntax_version=export_format)
    else:
        blob = json.load(inp)
        if mode.startswith('*'):
            n = blob.get('nex:nexml') or blob.get('nexml')
            if not n or (not isinstance(n, dict)):
                sys.exit('No top level "nex:nexml" element found. Document does not appear to be a JSON version of NeXML\n')
            if n:
                v = get_nexson_version(blob)
                if v.startswith('0'):
                    mode = 'b' + mode[1]
                else:
                    mode = 'j' + mode[1]

    if export_format == "nexml":
        syntax_version = BADGER_FISH_NEXSON_VERSION
        if mode.startswith('j'):
            syntax_version = DEFAULT_NEXSON_VERSION
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
            blob = convert_nexson_format(blob, export_format)
        json.dump(blob, out, indent=indentation, sort_keys=True)
        out.write('\n')

if __name__ == '__main__':
    _main()
