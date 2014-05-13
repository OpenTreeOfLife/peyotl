#!/usr/bin/env python
from peyotl.phylografter.nexson_workaround import workaround_phylografter_export_diffs, \
                                                             add_default_prop
from peyotl.phylesystem.git_actions import get_filepath_for_namespaced_id
from peyotl import get_logger
from subprocess import call
import codecs
import json
import sys
import os
import re
_LOG = get_logger(__name__)

def debug(m):
    _LOG.debug(m)

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
    sl = os.listdir(old_phylesystem_study)
for f in sl:
    if pg_study_pat.match(f):
        source_study = f
        dest_full = get_filepath_for_namespaced_id(new_phylesystem, f)
        scratch_dir = os.path.join(scratch_par, f)
        if not os.path.exists(scratch_dir):
            os.makedirs(scratch_dir)
        full_source = os.path.join(old_phylesystem_study, source_study, source_study + '.json')
        dest_dir = os.path.split(dest_full)[0]
        assert(os.path.exists(full_source))
        if os.path.exists(dest_full):
            debug('Skipping {} because output exists'.format(f))
            continue
        # read input and do the phylografter_workaround to valid 0.0.0 syntax
        # store in scratch.
        valid_bf = os.path.join(scratch_dir, 'v0.0.0-' + source_study + '.json')
        debug('Raw phylografter from "{}" to valid 0.0.0 NexSON at "{}" ...'.format(full_source, valid_bf))
        inp = codecs.open(full_source, mode='rU', encoding='utf-8')
        obj = json.load(inp)
        try:
            workaround_phylografter_export_diffs(obj, valid_bf)
        except:
            _LOG.exception('Exception in workaround_phylografter_export_diffs for study ' + f)
            failed.append(f)
            continue

        # Convert to 1.2.1
        unchecked_hbf = os.path.join(scratch_dir, 'v1.2.1-' + source_study + '.json')
        debug('Converting cleaned 0.0.0 NexSON from "{}" to unchecked 1.2.1 NexSON at "{}" ...'.format(valid_bf, unchecked_hbf))
        invoc = [sys.executable,
                 conversion_script, 
                '-s',
                '-e',
                '1.2.1',
                '-o',
                unchecked_hbf,
                valid_bf]
        debug('invoc: "{}"'.format('" "'.join(invoc)))
        rc = call(invoc)
        if rc != 0:
            failed.append(f)
        else:
            inp = codecs.open(unchecked_hbf, mode='rU', encoding='utf-8')
            obj = json.load(inp)
            aug_hbf = os.path.join(scratch_dir, 'augmentedv1.2.1-' + source_study + '.json')
            add_default_prop(obj, aug_hbf)
            # validate
            annotation = os.path.join(scratch_dir, 'validation.json')
            tmp = os.path.join(scratch_dir, 'final.json')
            debug('Writing annotated version of  "{}" to "{}" with annotations to "{}" ...'.format(
                    aug_hbf, 
                    tmp,
                    annotation))
            invoc = [sys.executable,
                     validation_script, 
                     '--embed',
                     '--agent-only',
                     '-e',
                      annotation,
                     '-o',
                     tmp,
                     aug_hbf]
            debug('invoc: "{}"'.format('" "'.join(invoc)))
            rc = call(invoc)
            if rc != 0:
                failed.append(f)
            else:
                if not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir)
                os.rename(tmp, dest_full)
if failed:
    m = '\n '.join(failed)
    sys.exit('Conversion of the following studies failed:\n {}'.format(m))