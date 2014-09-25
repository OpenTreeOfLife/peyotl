#!/usr/bin/env python
from peyotl.ott import OTT
from peyotl.utility import read_config, get_config_var, get_unique_filepath
from peyotl import get_logger
import subprocess
import os
_LOG = get_logger(__name__)
def _bail_if_file_not_found(p, fp):
    if not os.path.exists(fp):
        fp = os.path.abspath(fp)
        raise ValueError('The {p} filepath "{f}" does not exist'.format(p=p, f=fp))

def _treemachine_start(java_invoc,
                       treemachine_jar_path):
    if not isinstance(java_invoc, list):
        java_invoc = java_invoc.split(' ')
    else:
        java_invoc = list(java_invoc)
    _bail_if_file_not_found('treemachine jar', treemachine_jar_path)
    java_invoc.append('-jar')
    java_invoc.append(treemachine_jar_path)
    return java_invoc

def _run(cmd):
    pr = subprocess.Popen(cmd)
    rc = pr.wait()
    if rc != 0:
        f = "The external program invocation:\n  '{i}'\nfrom '{d}' failed."
        m = f.format(i="' '".join(cmd), d=os.path.abspath(os.curdir))
        raise RuntimeError(m)

def treemachine_load_taxonomy(java_invoc,
                           treemachine_jar_path,
                           ott,
                           taxonomy_db):
    _bail_if_file_not_found('taxonomy', ott.taxonomy_filepath)
    _bail_if_file_not_found('synonym', ott.synonyms_filepath)
    java_invoc = _treemachine_start(java_invoc, treemachine_jar_path)
    java_invoc.extend(['inittax', ott.taxonomy_filepath, ott.synonyms_filepath, ott.version, taxonomy_db])
    _run(java_invoc)

class GraphCommander(object):
    def __init__(self, config=None, read_config_files=None):
        if config is None:
            config = read_config()
        self._read_cfg_files = read_config_files
        self._cfg_obj = config
        self._used_var = {}
        self._taxonomy_db = None
        self._treemachine_jar = None
        self._java_invoc = None
        self._ott_dir = None
        self._ott = None
        self._trash_dir = None
    def _get_config_var(self, attr, section, param, default=None):
        value = get_config_var(section, param, default=default, cfg=self._cfg_obj)
        if value is None:
            f = 'The config parameter "{p}" in section "[{s}]" was not found.'
            m = f.format(p=param, s=section)
            if self._read_cfg_files:
                m += ' Config file(s) read were: "{}"'.format('", "'.join(self._read_cfg_files))
            raise RuntimeError(m)
        # store the values that we read, so that we can summarize, what config vars mattered...
        self._used_var[attr] = (value, section, param)
        return value
    @property
    def ott(self):
        if self._ott is None:
            self._ott = OTT(self.ott_dir)
        return self._ott
    @property
    def ott_dir(self):
        if self._ott_dir is None:
            self._ott_dir = self._get_config_var('ott_dir', 'ott', 'parent')
        return self._ott_dir
    @property
    def java_invoc(self):
        if self._java_invoc is None:
            self._java_invoc = self._get_config_var('java_invoc', 'treemachine', 'java', ['java', '-Xmx8g'])
        return self._java_invoc
    @property
    def treemachine_jar(self):
        if self._treemachine_jar is None:
            self._treemachine_jar = self._get_config_var('treemachine_jar', 'treemachine', 'jar')
        return self._treemachine_jar
    @property
    def taxonomy_db(self):
        if self._taxonomy_db is None:
            self._taxonomy_db = self._get_config_var('taxonomy_db', 'treemachine', 'tax_db')
        return self._taxonomy_db
    def _remove_filepath(self, fp):
        if os.path.exists(fp):
            self._remove_existing_filepath(fp)
    def _remove_existing_filepath(self, fp):
        afp = os.path.abspath(fp)
        if self._trash_dir is None:
            self._trash_dir = get_unique_filepath('graph-commander-trash')
            os.mkdir(self._trash_dir)
            self._trash_dir = os.path.abspath(self._trash_dir)
            f = '"{d}" directory created as location for items that would be overwritten'
            _LOG.info(f.format(d=self._trash_dir))
        if os.path.exists(afp):
            _LOG.info('Moving "{a}" inside "{t}"'.format(a=afp, t=self._trash_dir))
            fn = os.path.split(afp)[-1]
            os.rename(afp, os.path.join(self._trash_dir, fn))
    def load_taxonomy(self):
        tb = self.taxonomy_db
        self._remove_filepath(tb)
        treemachine_load_taxonomy(self.java_invoc, self.treemachine_jar, self.ott, tb)


