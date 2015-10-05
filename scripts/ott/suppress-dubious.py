#!/us/bin/env python
from peyotl import OTULabelStyleEnum
from peyotl import write_as_json
from peyotl.ott import OTT

if __name__ == '__main__':
    import argparse
    import codecs
    import sys
    import os
    description = 'Takes a ott directory, and output filename. Produces a newick representation of OTT with ' \
                  '"dubious" taxa pruned. Writes that newick to the specified file location.'
    parser = argparse.ArgumentParser(prog='suppress-dubious', description=description)
    parser.add_argument('--ott-dir',
                        default=None,
                        type=str,
                        required=True,
                        help='directory containing ott files (e.g "taxonomy.tsv")')
    parser.add_argument('--output',
                        default=None,
                        type=str,
                        required=True,
                        help='Output filepath for the newick.')
    parser.add_argument('--log',
                        default=None,
                        type=str,
                        required=False,
                        help='Optional output location of JSON file describing the operation')
    args = parser.parse_args(sys.argv[1:])
    ott_dir, output, log_filename = args.ott_dir, args.output, args.log
    try:
        assert os.path.isdir(args.ott_dir)
    except:
        sys.exit('Expecting ott-dir argument to be a directory. Got "{}"'.format(args.ott_dir))
    ott = OTT(ott_dir=args.ott_dir)
    create_log = log_filename is not None
    with codecs.open(args.output, 'w', encoding='utf-8') as outp:
        log = ott.write_newick(outp,
                               label_style=OTULabelStyleEnum.CURRENT_LABEL_OTT_ID,
                               prune_flags=ott.TREEMACHINE_SUPPRESS_FLAGS,
                               create_log_dict=create_log)
        outp.write('\n')
    if create_log:
        write_as_json(log, log_filename)
