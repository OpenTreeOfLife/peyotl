#!/usr/bin/env python
from peyotl.nexson_validation.phylografter_workaround import workaround_phylografter_export_diffs
from subprocess import call
import codecs
import json
import sys
import os
import re

def debug(m):
    sys.stderr.write(m)
    sys.stderr.write('\n')
    sys.stderr.flush()

old_phylesystem = sys.argv[1]
old_phylesystem_study = os.path.abspath(os.path.join(old_phylesystem, 'study'))
new_phylesystem = sys.argv[2]
new_phylesystem_study = os.path.abspath(os.path.join(new_phylesystem, 'study'))
scratch_par = sys.argv[3]
assert(os.path.isdir(old_phylesystem_study))
assert(os.path.isdir(new_phylesystem_study))
assert(os.path.isdir(scratch_par))

script_name = os.path.abspath(sys.argv[0])
peyotl_dev_dir = os.path.split(script_name)[0]
peyotl_dir =os.path.split(peyotl_dev_dir)[0]
conversion_script = os.path.join(peyotl_dir, 'scripts', 'nexson', 'nexson_nexml.py')
assert(os.path.isfile(conversion_script))
validation_script = os.path.join(peyotl_dir, 'scripts', 'nexson', 'validate_ot_nexson.py')
assert(os.path.isfile(conversion_script))
failed = []
pg_study_pat = re.compile(r'^\d+')

if len(sys.argv) > 4:
    sl = sys.argv[4:]
else:
    sl = sl
for f in sl:
    if pg_study_pat.match(f):
        source_study = f
        while len(f) < 2:
            f = '0' + f
        dest_topdir = 'pg_' + f[-2:]
        dest_subdir = 'pg_' + f
        dest_file = dest_subdir + '.json'
        dest_frag = os.path.join(dest_topdir, dest_subdir, dest_file)
        scratch_dir = os.path.join(scratch_par, f)
        if not os.path.exists(scratch_dir):
            os.makedirs(scratch_dir)
        full_source = os.path.join(old_phylesystem_study, source_study, source_study + '.json')
        dest_full = os.path.join(new_phylesystem_study, dest_frag)
        dest_dir = os.path.split(dest_full)[0]
        assert(os.path.exists(full_source))

        # read input and do the phylografter_workaround to valid 0.0.0 syntax
        # store in scratch.
        valid_bf = os.path.join(scratch_dir, 'v0.0.0-' + source_study + '.json')
        debug('Raw phylografter from "{}" to valid 0.0.0 NexSON at "{}" ...'.format(full_source, valid_bf))
        inp = codecs.open(full_source, mode='rU', encoding='utf-8')
        obj = json.load(inp)
        workaround_phylografter_export_diffs(obj, valid_bf)

        # Convert to 1.2.1
        unchecked_hbf = os.path.join(scratch_dir, 'v1.2.1-' + source_study + '.json')
        debug('Converting cleaned 0.0.0 NexSON from "{}" to unchecked 1.2.1 NexSON at "{}" ...'.format(valid_bf, unchecked_hbf))
        rc = call([sys.executable, conversion_script, 
                                    '-s',
                                    '-e',
                                    '1.2.1',
                                    '-o',
                                    unchecked_hbf,
                                    valid_bf])

        if rc != 0:
            failed.append(f)
        else:
            # Convert to 1.2.1
            annotation = os.path.join(scratch_dir, 'validation.json')
            tmp = os.path.join(scratch_dir, 'final.json')
            debug('Writing annotated version of  "{}" to "{}" with annotations to "{}" ...'.format(
                    unchecked_hbf, 
                    tmp,
                    annotation))
            rc = call([sys.executable, validation_script, 
                                        '--embed',
                                        '--agent-only',
                                        '-e',
                                        annotation,
                                        '-o',
                                        tmp,
                                        unchecked_hbf])
            if rc != 0:
                if os.path.exists(dest_full):
                    os.unlink(dest_full)
                failed(f)
            else:
                if not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir)
                os.rename(tmp, dest_full)

if failed:
    m = '\n '.join(failed)
    sys.exit('Conversion of the following studies failed:\n {}\n'.format(m))