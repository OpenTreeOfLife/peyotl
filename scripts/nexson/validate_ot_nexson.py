#!/usr/bin/env python
if __name__ == '__main__':
    from peyotl.nexson_syntax import write_as_json
    from peyotl.nexson_validation import NexsonError, \
                                         NexsonWarningCodes, \
                                         validate_nexson
    from peyotl import get_logger
    import argparse
    import codecs
    import json
    import sys
    import os
    SCRIPT_NAME = os.path.split(os.path.abspath(sys.argv[0]))[-1]
    _LOG = get_logger(SCRIPT_NAME)
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

    parser = argparse.ArgumentParser(description='Validate a json file as Open Tree of Life NexSON')
    parser.add_argument('--verbose',
                        dest='verbose',
                        action='store_true',
                        default=False,
                        help='verbose output')
    parser.add_argument('--agent-only',
                        dest='add_agent_only',
                        action='store_true',
                        default=False,
                        help='If --embed and this argument are both used, only the agent info will be embedded in the annotation')
    out_syntax_choices = ["json",]
    out_syntax_choices.sort()
    s_help = 'Syntax of output. Valid choices are: "{c}"'.format(c='", "'.join(out_syntax_choices))
    parser.add_argument("-s", "--syntax", 
                        metavar="FMT",
                        required=False,
                        choices=out_syntax_choices,
                        default="json",
                        help=s_help)
    parser.add_argument("-o", "--output", 
                        metavar="FILE",
                        required=False,
                        help="output filepath. Standard output is used if omitted.")
    parser.add_argument("-e", "--err-stream", 
                        metavar="FILE",
                        required=False,
                        dest='err_fn',
                        help="error stream filepath. Standard error is used if omitted.")
    parser.add_argument('--meta',
                        dest='meta',
                        action='store_true',
                        default=False,
                        help='warn about unvalidated meta elements')
    parser.add_argument('--embed',
                        dest='embed',
                        action='store_true',
                        default=False,
                        help='Writes warnings/errors into the NexSON content')
    parser.add_argument('input',
                        metavar='filepath',
                        type=unicode,
                        nargs=1,
                        help='filename')
    err_stream = sys.stderr
    args = parser.parse_args()
    try:
        inp_filepath = args.input[0]
    except:
        sys.exit('Expecting a filepath to a NexSON file as the only argument.\n')
    inp = codecs.open(inp_filepath, 'rU', encoding='utf-8')
    outfn = args.output
    if outfn is not None:
        try:
            out = codecs.open(outfn, mode='w', encoding='utf-8')
        except:
            sys.exit('validate_ot_nexson: Could not open output filepath "{fn}"\n'.format(fn=outfn))
    else:
        out = codecs.getwriter('utf-8')(sys.stdout)
    errfn = args.err_fn
    if errfn is not None:
        try:
            err_stream = codecs.open(errfn, mode='w', encoding='utf-8')
        except:
            sys.exit('validate_ot_nexson: Could not open err-stream filepath "{fn}"\n'.format(fn=errfn))
    try:
        obj = json.load(inp)
    except ValueError as vx:
        _LOG.error('Not valid JSON.')
        if args.verbose:
            raise vx
        else:
            sys.exit(1)
    codes_to_skip = None
    if not args.meta:
        codes_to_skip = [NexsonWarningCodes.UNVALIDATED_ANNOTATION]
    try:
        v_log, adaptor = validate_nexson(obj, codes_to_skip)
    except NexsonError as nx:
        _LOG.error(nx.value)
        sys.exit(1)
    rc = 0
    if args.embed:
        rc = 1 if v_log.has_error() else 0
        annotation = v_log.prepare_annotation(author_name=SCRIPT_NAME,
                                              invocation=sys.argv[1:],
                                              )
        adaptor.add_or_replace_annotation(obj,
                                          annotation['annotationEvent'],
                                          annotation['agent'],
                                          add_agent_only=args.add_agent_only)
        write_as_json(obj, out)
        if args.add_agent_only:
            write_as_json(annotation['annotationEvent'], err_stream, indent=2)
        rc = len(v_log.errors)
    else:
        if (not v_log.errors) and (not v_log.warnings):
            _LOG.info('Valid')
        else:
            rc = len(v_log.errors)
            if args.syntax.lower() == 'json':
                em_dict = v_log.get_err_warn_summary_dict()
                if em_dict:
                    json.dump(em_dict, out, indent=2, sort_keys=True)
                    out.write('\n')
            else:
                if v_log.errors:
                    for el in v_log.errors:
                        _LOG.error(el)
                else:
                    for el in v_log.warnings:
                        _LOG.warn(el)
    sys.exit(rc)
