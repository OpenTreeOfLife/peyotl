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

# list of the absolute path to the each of the known "study" directories in phylesystem repos.
_study_dirs = []

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
    repos=[]
    for p in x:
        if not os.path.isdir(p):
            raise ValueError('No phylesystem parent "{p}" is not a directory'.format(p=p))            
        repos=repos+[ os.path.join(p,name) for name in os.listdir(p) if os.path.isdir(os.path.join(p, name+'/.git')) ]
    if not repos:
        raise ValueError('No git repos in {parent}'.format{})
    return repos

      
    
    
def _initialize_study_index():
    d = {} # Key is study id, value is repo,dir tuple
    #if not 
    for x in _get_phylesystem_parent():
      for root, dirs, files in os.walk(x):      
       for file in files:
         if ".git" not in root:
             d[file]=root    # if file is in more than one place it gets over written. EJM Needs work 
    return d

def get_paths_for_study_id(study_id):
    global _study_index, _study_index_lock
    _study_index_lock.acquire()
    try:
        if _study_index is None:
            _study_index = _initialize_study_index()
        _study_index[study_id]
    finally:
        _study_index_lock.release()

def _search_for_repo_dirs(par):
    for n in os.listdir(par):
        if not n.startswith('phylesystem'): #TEMP Hardcode repo name pattern
            continue
        fp = os.path.join(par, n)
        if os.path.isdir(fp):
            d = os.path.abspath(fp)
            s = os.path.join(d, 'study') #TEMP Hardcode file name pattern
            if os.path.exists(s):
                if s not in _study_dirs:
                    _study_dirs.append(s)

def _iter_phylesystem_repos(study_dir_list=None,
                            parent_list=None):
    if study_dir_list is None:
        if not _study_dirs:
            search_for_study_dirs(parent_list)
        study_dir_list = _study_dirs
    for i in study_dir_list:
        yield i

def phylesystem_study_paths(study_dir_list=None,
                            parent_list=None):
    '''Generator that allows you to iterate over all detected phylesystem
    studies.
    See documentation about specifying PHYLESYSTEM_PARENT
    '''
    for p in _iter_phylesystem_repos(study_dir_list=study_dir_list,
                                     parent_list=parent_list):
        sub = os.listdir(p)
        sub.sort()
        for c in sub:
            sp = os.path.join(p, c)
            if os.path.isdir(sp):
                fp = os.path.join(sp, c + '.json') #TEMP Hardcode file name pattern
                if os.path.isfile(fp):
                    yield (c, fp)

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

#----------------------------------------------------------------------
#From get_study_index in api, might repeat above?





def create_new_path_for_study_id(study_id):
    global _study_index, _study_index_lock
    _study_index_lock.acquire()
    try:
        pass
    finally:
        _study_index_lock.release()

try:
    get_paths_for_study_id('abdha')
except:
    pass

                
def write_study(jsondat,repo=repo_path):
    tmpname="tmp.txt"
    fi=open(tmp.txt)
    fi.write(jsondat)
    fi.close()
    phylesystem.GitAction(repo)
    
    
    
   
