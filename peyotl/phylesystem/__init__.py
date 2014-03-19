#!/usr/bin/env python
'''Utilities for dealing with local filesystem
copies of the phylesystem repositories.
'''
from peyotl.utility import get_config, expand_path
try:
    import anyjson
except:
    import json
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads
import codecs
import os
from threading import Lock
_study_index_lock = Lock()
_study_index = None


def get_HEAD_SHA1(git_dir):
    '''Not locked!
    '''
    head_file = os.path.join(git_dir, 'HEAD')
    with open(head_file, 'rU') as hf:
        head_contents = hf.read().strip()
    assert(head_contents.startswith('ref: '))
    ref_filename = head_contents[5:] #strip off "ref: "
    real_ref = os.path.join(git_dir, ref_filename)
    with open(real_ref, 'rU') as rf:
        return rf.read().strip()

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


def get_repos():
    _repos = {} # key is repo name, value repo location
    par_list = _get_phylesystem_parent()
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
            if ".json" in filename:
                # if file is in more than one place it gets over written.
                #TODO EJM Needs work 
                d[filename] = (tag, root)
    return d

def _initialize_study_index():
    d = {} # Key is study id, value is repo,dir tuple
    repos = get_repos()
    for repo in _repos:
        p = os.path.join(_repos[repo], 'study')
        dr = create_id2repo_pair_dict(p, repo)
        d.update(dr)
    return d

def get_paths_for_study_id(study_id):
    global _study_index
    _study_index_lock.acquire()
    if ".json" not in study_id:
         study_id=study_id+".json" #@EJM risky?
    try:
        if _study_index is None:
            _study_index = _initialize_study_index()
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

class Phylesystem(object):
    '''Wrapper around a set of sharded git repos'''
    def __init__(self, repos_dict=None):
        if repos_dict is None:
            repos_dict = get_repos()
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

