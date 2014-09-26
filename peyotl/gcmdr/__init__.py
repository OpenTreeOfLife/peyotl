#!/usr/bin/env python
from peyotl.utility import read_config, get_config_var, get_unique_filepath
from peyotl.nexson_syntax import create_content_spec, get_git_sha, read_as_json, write_as_json
from peyotl.api import PhylesystemAPI
from peyotl import get_logger
from peyotl.ott import OTT
import subprocess
import tempfile
import codecs
import shutil
import os
_LOG = get_logger(__name__)
VERBOSE = True
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

def _run(cmd, stdout=None, stderr=subprocess.STDOUT):
    try:
        if VERBOSE:
            f = "Calling:\n  '{i}'\nfrom '{d}'..."
            m = f.format(i="' '".join(cmd), d=os.path.abspath(os.curdir))
            _LOG.debug(m)
        pr = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
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


def treemachine_load_one_tree(java_invoc,
                              treemachine_jar_path,
                              db_path,
                              study_filepath,
                              tree_id,
                              log_filepath,
                              testing=False):
    _bail_if_file_not_found('study file', study_filepath)
    _bail_if_file_not_found('load db', db_path)
    nexson = read_as_json(study_filepath)
    sha = get_git_sha(nexson)
    java_invoc = _treemachine_start(java_invoc, treemachine_jar_path)
    java_invoc.extend(['pgloadind', db_path, study_filepath, tree_id, sha])
    verb = 'loading'
    if testing:
        java_invoc.append('f')
        verb = 'testing'
    _LOG.debug('{v} tree {t} from NexSON from "{p}" and logging to "{l}"'.format(v=verb,
                                                                                 t=tree_id,
                                                                                 p=study_filepath,
                                                                                 l=log_filepath))
    with codecs.open(log_filepath, 'a', encoding='utf-8') as logf:
        _run(java_invoc, stdout=logf)
    return sha

def treemachine_map_compat_one_tree(java_invoc, treemachine_jar, db_path, study_id, tree_id, sha):
    _bail_if_file_not_found('load db', db_path)
    java_invoc = _treemachine_start(java_invoc, treemachine_jar)
    tm_key = to_treemachine_name(study_id, tree_id, sha)
    java_invoc.extend(['mapcompat', db_path, tm_key])
    _LOG.debug('calling mapcompat for tree key {}'.format(tm_key))
    return _run_return_content(java_invoc)

def _run_return_content(invoc):
    tmpfh, tmpfn = tempfile.mkstemp()
    os.close(tmpfh)
    try:
        with codecs.open(tmpfn, 'w', encoding='utf-8') as tmpfo:
            _run(invoc, stdout=tmpfo, stderr=subprocess.PIPE)
        with codecs.open(tmpfn, 'rU', encoding='utf-8') as tmpfo:
            content = tmpfo.read()
        return content
    finally:
        os.remove(tmpfn)

def to_treemachine_name(study_id=None, tree_id=None, sha=None, obj=None):
    if obj is not None:
        study_id = obj.get('study_id', study_id)
        tree_id = obj.get('tree_id', tree_id)
        sha = obj.get('sha', sha)
    return '{s}_{t}_{g}'.format(s=study_id, t=tree_id, g=sha)

def treemachine_source_explorer(java_invoc, treemachine_jar, db, study_id, tree_id, sha):
    '''Runs sourceexplorer and returns the stdout.'''
    _bail_if_file_not_found('load db', db)
    java_invoc = _treemachine_start(java_invoc, treemachine_jar)
    tm_key = to_treemachine_name(study_id, tree_id, sha)
    java_invoc.extend(['sourceexplorer', tm_key, db])
    return _run_return_content(java_invoc).strip()
def treemachine_extract_synthesis(java_invoc, treemachine_jar, synth_db, synth_ott_id):
    _bail_if_file_not_found('synthesis db', synth_db)
    java_invoc = _treemachine_start(java_invoc, treemachine_jar)
    tmpfh, tmpfn = tempfile.mkstemp()
    os.close(tmpfh)
    java_invoc.extend(['extractdrafttree_ottid', synth_ott_id, tmpfn, synth_db])
    try:
        _run(java_invoc)
        with codecs.open(tmpfn, 'rU', encoding='utf-8') as tmpfo:
            content = tmpfo.read()
        return content
    finally:
        os.remove(tmpfn)
def treemachine_synthesize(java_invoc, treemachine_jar, synth_db, synth_ott_id, loaded, log_filepath):
    _bail_if_file_not_found('synthesis db', synth_db)
    java_invoc = _treemachine_start(java_invoc, treemachine_jar)
    tm_list = [to_treemachine_name(obj=i) for i in loaded]
    tm_list.append('taxonomy')
    java_invoc.extend(['synthesizedrafttreelist_ottid', synth_ott_id, ','.join(tm_list), synth_db])
    _run(java_invoc, stdout=codecs.open(log_filepath, 'a', encoding='utf-8'))

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
        self._load_db = None
        self._log_filepath = None
        self._nexson_cache = None
        self._ott_dir = None
        self._ott = None
        self._taxonomy_db = None
        self._tree_log = None
        self._treemachine_jar = None
        self._trash_dir = None
        self._phylesystem_api = None
    # this set of dummy functions are replaced by monkey punching below.
    # the definitions here keep pylint from complaining.
    def taxonomy_db(self):
        return ''
    java_invoc = taxonomy_db
    load_db = taxonomy_db
    log_filepath = taxonomy_db
    loaded_trees_json = taxonomy_db
    nexson_cache = taxonomy_db
    ott_dir = taxonomy_db
    synthesis_db = taxonomy_db
    synth_ott_id = taxonomy_db
    tree_log = taxonomy_db
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
            # trigger helpful message if config is not found
            self._get_config_var('phylesystem_api_parent', 'phylesystem', 'parent', None)
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
    def fetch_nexsons(self, tree_list, download=False):
        nc = self.nexson_cache
        pa = self.phyleystem_api
        if download:
            pa.phylesystem_obj.pull()
        schema = create_content_spec(nexson_version='0.0.0')
        for id_obj in tree_list:
            study_id = id_obj['study_id']
            nexson = pa.get_study(study_id, schema=schema)
            path = os.path.join(nc, study_id)
            write_as_json(nexson, path)
    def synthesize(self,
                   reinitialize=True):
        synth_db = self.synthesis_db
        synth_ott_id = self.synth_ott_id
        log_filepath = self.log_filepath
        if reinitialize:
            load_db = self.load_db
            if os.path.abspath(load_db) != os.path.abspath(synth_db):
                if not os.path.exists(load_db):
                    f = 'loading a graph with reinitialize requies that the trees have been loaded into a loading db'
                    raise RuntimeError(f)
                self._remove_filepath(synth_db)
                _LOG.debug('copying "{s}" to "{d}"'.format(s=load_db, d=synth_db))
                shutil.copytree(load_db, synth_db)
        loaded_trees_json = self.loaded_trees_json
        if not os.path.exists(loaded_trees_json):
            f = '"{}" does not exist, so I can not tell what studies have been loaded'
            raise RuntimeError(f.format(loaded_trees_json))
        loaded = read_as_json(loaded_trees_json)
        return treemachine_synthesize(self.java_invoc, self.treemachine_jar, synth_db, synth_ott_id, loaded, log_filepath)

    def extract_synthesis(self):
        synth_db = self.synthesis_db
        synth_ott_id = self.synth_ott_id
        tree_log = self.tree_log
        tree_str = treemachine_extract_synthesis(self.java_invoc,
                                                 self.treemachine_jar,
                                                 synth_db,
                                                 synth_ott_id)
        with codecs.open(tree_log, 'a', encoding='utf-8') as tree_fo:
            tree_fo.write(tree_str)
            tree_fo.write('\n')
        print tree_str

    def load_graph(self,
                   tree_list,
                   reinitialize=False,
                   testing=False,
                   report=True,
                   map_compat=True):
        tb = self.load_db
        nc = self.nexson_cache
        log_filepath = self.log_filepath
        tree_log = self.tree_log
        loaded_trees_json = self.loaded_trees_json
        for id_obj in tree_list:
            study_id = id_obj['study_id']
            path = os.path.join(nc, study_id)
            if not os.path.exists(path):
                f = 'Study file not found at "{p}". All studies must be fetched before they can be loaded.'
                raise RuntimeError(f.format(p=path))
        if os.path.exists(loaded_trees_json):
            loaded = read_as_json(loaded_trees_json)
        else:
            loaded = []
        if reinitialize:
            tax_db = self.taxonomy_db
            if os.path.abspath(tax_db) != os.path.abspath(tb):
                if not os.path.exists(tax_db):
                    f = 'loading a graph with reinitialize requies that the taxonomy has been loaded into a taxonomy db'
                    raise RuntimeError(f)
                self._remove_filepath(tb)
                _LOG.debug('copying "{s}" to "{d}"'.format(s=tax_db, d=tb))
                shutil.copytree(tax_db, tb)
                if os.path.exists(loaded_trees_json):
                    os.remove(loaded_trees_json)
                loaded = []

        for id_obj in tree_list:
            study_id = id_obj['study_id']
            tree_id = id_obj['tree_id']
            path = os.path.join(nc, study_id)
            sha = treemachine_load_one_tree(self.java_invoc,
                                            self.treemachine_jar,
                                            tb,
                                            path,
                                            tree_id,
                                            log_filepath,
                                            testing=testing)
            loaded.append({'study_id':study_id, 'tree_id': tree_id, 'sha': sha})
            write_as_json(loaded, loaded_trees_json)
            if report:
                tree_str = self._report_source_tree(tb, study_id, tree_id, sha)
                with codecs.open(tree_log, 'a', encoding='utf-8') as tree_fo:
                    tree_fo.write(tree_str)
                    tree_fo.write('\n')
                print tree_str
            if map_compat:
                map_content = treemachine_map_compat_one_tree(self.java_invoc,
                                                              self.treemachine_jar,
                                                              tb,
                                                              study_id,
                                                              tree_id,
                                                              sha)
                with codecs.open(log_filepath, 'a', encoding='utf-8') as log_fo:
                    log_fo.write(map_content)
                print map_content

    def _report_source_tree(self, db, study_id, tree_id, sha):
        return treemachine_source_explorer(self.java_invoc,
                                           self.treemachine_jar,
                                           db,
                                           study_id,
                                           tree_id,
                                           sha)






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
               'load_db': ('treemachine', 'load_db', None),
               'loaded_trees_json': ('treemachine', 'loaded_trees_json', None),
               'log_filepath': ('treemachine', 'log', None),
               'nexson_cache': ('treemachine', 'nexson_cache', None),
               'ott_dir': ('ott', 'parent', None),
               'synthesis_db': ('treemachine', 'synthesis_db', None),
               'synth_ott_id': ('treemachine', 'synth_ott_id', None),
               'taxonomy_db': ('treemachine', 'tax_db', None),
               'tree_log': ('treemachine', 'out_tree_file', None),
               'treemachine_jar': ('treemachine', 'jar', None), }

monkey_patch_with_config_vars(GraphCommander, _PROPERTIES)
