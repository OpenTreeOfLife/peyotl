#!/usr/bin/env python
from peyotl.utility import read_config, get_config_var, get_unique_filepath
from peyotl.nexson_syntax import create_content_spec, write_as_json
from peyotl.api import PhylesystemAPI
from peyotl import get_logger
from peyotl.ott import OTT
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
    try:
        pr = subprocess.Popen(cmd)
        rc = pr.wait()
    except:
       rc = -1
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


class PropertiesFromConfig(object):
    def __init__(self, config=None, read_config_files=None):
        if config is None:
            config = read_config()
        self._read_cfg_files = read_config_files
        self._cfg_obj = config
        self._used_var = {}
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
class GraphCommander(PropertiesFromConfig):
    def __init__(self, config=None, read_config_files=None):
        PropertiesFromConfig.__init__(self, config=config, read_config_files=read_config_files)
        self._java_invoc = None
        self._nexson_cache = None
        self._ott_dir = None
        self._ott = None
        self._taxonomy_db = None
        self._treemachine_jar = None
        self._trash_dir = None
        self._phylesystem_api = None
    # this set of dummy functions are replaced by monkey punching below.
    # the definitions here keep pylint from complaining.
    def taxonomy_db(self):
        return ''
    java_invoc = taxonomy_db
    nexson_cache = taxonomy_db
    ott_dir = taxonomy_db
    treemachine_jar = taxonomy_db
    # end dummy property defs
    @property
    def ott(self):
        if self._ott is None:
            self._ott = OTT(self.ott_dir)
        return self._ott
    @property
    def phyleystem_api(self):
        if self._phylesystem_api is None:
            # trigger helpful message
            p = self._get_config_var('phylesystem_api_parent', 'phylesystem', 'parent', None)
            pa = PhylesystemAPI(get_from='local')
            self._phylesystem_api = pa
        return self._phylesystem_api

    def _remove_filepath(self, fp):
        assert fp is not None
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
    def fetch_nexsons(self, tree_list):
        nc = self.nexson_cache
        pa = self.phyleystem_api
        schema = create_content_spec(nexson_version='0.0.0')
        for id_obj in tree_list:
            study_id = id_obj['study_id']
            nexson = pa.get_study(study_id, schema=schema)
            path = os.path.join(nc, study_id)
            write_as_json(nexson, path)
            



def monkey_patch_with_config_vars(_class, _properties):
    '''_class will have new read-only properites added.
    _properties keys will be the names. The
    value for the key should be (config section, config param name, default)
    _class should be derived from PropertiesFromConfig
    '''
    for prop_name, config_info in _properties.items():
        real_att_name = '_' + prop_name
        def getter(self, ran=real_att_name, ci=config_info, pn=prop_name):
            v = getattr(self, ran, None) 
            if v is None:
                v = self._get_config_var(pn, ci[0], ci[1], ci[2])
                setattr(self, ran, v)
            return v
        setattr(GraphCommander, prop_name, property(getter))

_PROPERTIES = {'java_invoc': ('treemachine', 'java', ['java', '-Xmx8g']),
               'nexson_cache': ('treemachine', 'nexson_cache', None),
               'ott_dir': ('ott', 'parent', None),
               'taxonomy_db': ('treemachine', 'tax_db', None),
               'treemachine_jar': ('treemachine', 'jar', None), }

monkey_patch_with_config_vars(GraphCommander, _PROPERTIES)
