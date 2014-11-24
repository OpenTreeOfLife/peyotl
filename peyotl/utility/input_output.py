#!/usr/bin/env python
'''Simple utility functions for Input/Output do not depend on any other part of
peyotl.
'''
from peyotl.utility.str_util import is_str_type
import codecs
import json
import stat
import os

def open_for_group_write(fp, mode, encoding='utf-8'):
    '''Open with mode=mode and permissions '-rw-rw-r--' group writable is
    the default on some systems/accounts, but it is important that it be present on our deployment machine
    '''
    d = os.path.split(fp)[0]
    if not os.path.exists(d):
        os.makedirs(d)
    o = codecs.open(fp, mode, encoding=encoding)
    o.flush()
    os.chmod(fp, stat.S_IRGRP | stat.S_IROTH | stat.S_IRUSR | stat.S_IWGRP | stat.S_IWUSR)
    return o
def read_filepath(filepath, encoding='utf-8'):
    with codecs.open(filepath, 'r', encoding=encoding) as fo:
        return fo.read()


def write_to_filepath(content, filepath, encoding='utf-8', mode='w', group_writeable=False):
    '''Writes `content` to the `filepath` Creates parent directory
    if needed, and uses the specified file `mode` and data `encoding`.
    If `group_writeable` is True, the output file will have permissions to be
        writable by the group (on POSIX systems)
    '''
    par_dir = os.path.split(filepath)[0]
    if not os.path.exists(par_dir):
        os.makedirs(par_dir)
    if group_writeable:
        with open_for_group_write(filepath, mode=mode, encoding=encoding) as fo:
            fo.write(content)
    else:
        with codecs.open(filepath, mode=mode, encoding=encoding) as fo:
            fo.write(content)

def expand_path(p):
    return os.path.expanduser(os.path.expandvars(p))

def download(url, encoding='utf-8'):
    import requests
    response = requests.get(url)
    response.encoding = encoding
    return response.text

def write_as_json(blob, dest, indent=0, sort_keys=True):
    opened_out = False
    if is_str_type(dest):
        out = codecs.open(dest, mode='w', encoding='utf-8')
        opened_out = True
    else:
        out = dest
    try:
        json.dump(blob, out, indent=indent, sort_keys=sort_keys)
        out.write('\n')
    finally:
        out.flush()
        if opened_out:
            out.close()

def read_as_json(infi, encoding='utf-8'):
    with codecs.open(infi, 'r', encoding=encoding) as inpf:
        n = json.load(inpf)
    return n

def parse_study_tree_list(fp):
    '''study trees should be in {'study_id', 'tree_id'} objects, but
    as legacy support we also need to support files that have the format:
    pg_315_4246243 # comment

    '''
    try:
        sl = read_as_json(fp)
    except:
        sl = []
        with codecs.open(fp, 'rU', encoding='utf-8') as fo:
            for line in fo:
                frag = line.split('#')[0].strip()
                if frag:
                    sl.append(frag)
    ret = []
    for element in sl:
        if isinstance(element, dict):
            assert 'study_id' in element
            assert 'tree_id' in element
            ret.append(element)
        else:
            assert element.startswith('pg_') or element.startswith('ot_')
            s = element.split('_')
            assert len(s) > 1
            tree_id = s[-1]
            study_id = '_'.join(s[:-1])
            ret.append({'study_id': study_id, 'tree_id': tree_id})
    return ret


