#!/usr/bin/env python
'''Utilities for dealing with local filesystem
copies of the phylesystem repositories.
'''
from peyotl.utility import get_config, expand_path, get_logger
try:
    import anyjson
except:
    import json
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads
try:
    from dogpile.cache import NO_VALUE
except:
    pass #caching is optional
from peyotl.phylesystem.git_workflows import __validate
from peyotl.nexson_syntax import detect_nexson_version
from peyotl.nexson_validation._validation_base import NexsonAnnotationAdder
import codecs
import os
from threading import Lock
_LOG = get_logger(__name__)
_study_index_lock = Lock()
_study_index = None


def _get_phylesystem_parent():
    if 'PHYLESYSTEM_PARENT' in os.environ:
        phylesystem_parent = os.environ.get('PHYLESYSTEM_PARENT')
    else:
        try:
            phylesystem_parent = expand_path(get_config('phylesystem', 'parent'))
        except:
            raise ValueError('No phylesystem parent specified in config or environmental variables')
    x = phylesystem_parent.split(':') #TEMP hardcoded assumption that : does not occur in a path name
    return(x)


def get_repos(par_list=None):
    _repos = {} # key is repo name, value repo location
    if par_list is None:
        par_list = _get_phylesystem_parent()
    elif not isinstance(par_list, list):
        par_list = [par_list]
    for p in par_list:
        if not os.path.isdir(p):
            raise ValueError('No phylesystem parent "{p}" is not a directory'.format(p=p))            
        for name in os.listdir(p):
            if os.path.isdir(os.path.join(p, name + '/.git')):
                _repos[name] = os.path.join(p, name)
    if len(_repos) == 0:
        raise ValueError('No git repos in {parent}'.format(str(par_list)))
    return _repos

def create_id2repo_pair_dict(path, tag):
    d = {}
    for triple in os.walk(path):
        root, files = triple[0], triple[2]
        for filename in files:
            if filename.endswith('.json'):
                # if file is in more than one place it gets over written.
                #TODO EJM Needs work 
                study_id = filename[:-5]
                d[study_id] = (tag, root)
    return d

def _initialize_study_index(repos_par=None):
    d = {} # Key is study id, value is repo,dir tuple
    repos = get_repos(repos_par)
    for repo in _repos:
        p = os.path.join(_repos[repo], 'study')
        dr = create_id2repo_pair_dict(p, repo)
        d.update(dr)
    return d

def get_paths_for_study_id(study_id, repos_par=None):
    global _study_index
    _study_index_lock.acquire()
    if ".json" not in study_id:
         study_id=study_id+".json" #@EJM risky?
    try:
        if _study_index is None:
            _study_index = _initialize_study_index(repos_par)
        return _study_index[study_id]
    except KeyError, e:
        raise ValueError("Study {} not found in repo".format(study_id))
    finally:
        _study_index_lock.release()

def create_new_path_for_study_id(study_id):
    _study_index_lock.acquire()
    try:
        pass
    finally:
        _study_index_lock.release()

def phylesystem_study_objs(**kwargs):
    '''Generator that iterates over all detected phylesystem studies.
    Returns a pair (study_id, study_obj)
    See documentation about specifying PHYLESYSTEM_PARENT
    '''
    for study_id, fp in phylesystem_study_paths(**kwargs):
        with codecs.open(fp, 'rU', 'utf-8') as fo:
            try:
                nex_obj = anyjson.loads(fo.read())['nexml']
                yield (study_id, nex_obj)
            except Exception:
                pass

class PhylesystemShard(object):
    '''Wrapper around a git repos holding nexson studies'''
    def __init__(self, name, path):
        self.name = name
        dot_git = os.path.join(path, '.git')
        study_dir = os.path.join(path, 'study')
        if not os.path.isdir(path):
            raise ValueError('"{p}" is not a directory'.format(p=path))
        if not os.path.isdir(dot_git):
            raise ValueError('"{p}" is not a directory'.format(p=dot_git))
        if not os.path.isdir(study_dir):
            raise ValueError('"{p}" is not a directory'.format(p=study_dir))
        d = create_id2repo_pair_dict(study_dir, name)
        self._study_index = d
        self.path = path
        self.git_dir = dot_git
        self.study_dir = study_dir
    def get_study_index(self):
        return self._study_index
    study_index = property(get_study_index)
    def diagnose_repo_nexml2json(self):
        fp = self.study_index.values()[0]
        with codecs.open(fp, mode='rU', encoding='utf-8') as fo:
            fj = json.load(fo)
            return detect_nexson_version(fj)


_CACHE_REGION_CONFIGURED = False
def make_phylesystem_cache_region():
    global _CACHE_REGION_CONFIGURED
    if _CACHE_REGION_CONFIGURED:
        return
    _CACHE_REGION_CONFIGURED = True
    try:
        from dogpile.cache import make_region
    except:
        _LOG.debug('dogpile.cache not available')
        return
    first_par = _get_phylesystem_parent()[0]
    cache_db_dir = os.path.split(first_par)[0]
    cache_db = os.path.join(cache_db_dir, 'phylesystem-cachefile.dbm')
    _LOG.debug('dogpile.cache region using "{}"'.format(cache_db))
    try:
        a = {'filename': cache_db}
        region = make_region().configure('dogpile.cache.dbm',
                                         expiration_time = 36000,
                                         arguments = a)
        _LOG.debug('cache region set up.')
    except:
        _LOG.exception('cache set up failed')

class Phylesystem(object):
    '''Wrapper around a set of sharded git repos'''
    def __init__(self,
                 repos_dict=None,
                 repos_par=None,
                 with_caching=True,
                 repo_nexml2json=None):
        if repos_dict is None:
            repos_dict = get_repos(repos_par)
        shards = []
        for repo_name, repo_filepath in repos_dict.items():
            shards.append(PhylesystemShard(repo_name, repo_filepath))
        d = {}
        for s in shards:
            for k, v in s.study_index.items():
                if k in d:
                    raise KeyError('study "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._study2shard_map = d
        self._shards = shards
        if repo_nexml2json is None:
            try:
                repo_nexml2json = get_config('phylesystem', 'repo_nexml2json')
            except:
                repo_nexml2json = shards[0].diagnose_repo_nexml2json()
        self.repo_nexml2json = repo_nexml2json
        if with_caching:
            self._cache_region = make_phylesystem_cache_region()
        else:
            self._cache_region = None


    def create_git_action(self, study_id):
        shard = self._study2shard_map[study_id]
        from peyotl.phylesystem.git_actions import GitAction
        return GitAction(repo=shard.path)

    def add_validation_annotation(self, study_obj, sha):
        adaptor = None
        if self._cache_region is not None:
            key = 'v' + sha
            annot_event = self._cache_region.get(key, ignore_expiration=True)
            if annot_event != NO_VALUE:
                adaptor = NexsonAnnotationAdder()
        if adaptor is None:
            bundle = __validate(study_obj)
            annotation = bundle[0]
            annot_event = annotation['annotationEvent']
            adaptor = bundle[2]
        adaptor.replace_same_agent_annotation(nexson, annot_event)
        if self._cache_region is not None:
            self._cache_region.set(key, annot_event)




