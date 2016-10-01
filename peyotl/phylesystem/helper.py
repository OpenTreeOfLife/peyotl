from peyotl.utility import expand_path, get_logger, get_config_setting
import json
try:
    import anyjson
except:
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads
from peyotl.phylesystem.git_actions import get_filepath_for_namespaced_id, \
                                           get_filepath_for_simple_id
import os
import re
from threading import Lock
_LOG = get_logger(__name__)
_study_index_lock = Lock()

def _get_phylesystem_parent_with_source(**kwargs):
    src = 'environment'
    try:
        phylesystem_parent = expand_path(get_config_setting('phylesystem', 'parent'))
        src = 'configfile'
    except:
        raise ValueError('No [phylesystem] "parent" specified in config or environmental variables')
    x = phylesystem_parent.split(':') #TEMP hardcoded assumption that : does not occur in a path name
    return x, src

def _get_phylesystem_parent(**kwargs):
    return _get_phylesystem_parent_with_source(**kwargs)[0]


def get_repos(par_list=None, **kwargs):
    '''Returns a dictionary of name -> filepath
    `name` is the repo name based on the dir name (not the get repo). It is not
        terribly useful, but it is nice to have so that any mirrored repo directory can
        use the same naming convention.
    `filepath` will be the full path to the repo directory (it will end in `name`)
    '''
    _repos = {} # key is repo name, value repo location
    if par_list is None:
        par_list = _get_phylesystem_parent(**kwargs)
    elif not isinstance(par_list, list):
        par_list = [par_list]
    for p in par_list:
        if not os.path.isdir(p):
            raise ValueError('Phylesystem parent "{p}" is not a directory'.format(p=p))
        for name in os.listdir(p):
            #TODO: Add an option to filter just phylesystem repos (or any specified type?) here!
            #  - add optional list arg `allowed_repo_names`?
            #  - let the FailedShardCreationError work harmlessly?
            #  - treat this function as truly for phylesystem only?
            if os.path.isdir(os.path.join(p, name + '/.git')):
                _repos[name] = os.path.abspath(os.path.join(p, name))
    if len(_repos) == 0:
        raise ValueError('No git repos in {parent}'.format(parent=str(par_list)))
    return _repos

def create_id2study_info(path, tag):
    '''Searchers for *.json files in this repo and returns
    a map of study id ==> (`tag`, dir, study filepath)
    where `tag` is typically the shard name
    '''
    d = {}
    for triple in os.walk(path):
        root, files = triple[0], triple[2]
        for filename in files:
            if filename.endswith('.json'):
                study_id = filename[:-5]
                d[study_id] = (tag, root, os.path.join(root, filename))
    return d

def _initialize_study_index(repos_par=None, **kwargs):
    d = {} # Key is study id, value is repo,dir tuple
    repos = get_repos(repos_par, **kwargs)
    for repo in repos:
        p = os.path.join(repos[repo], 'study')
        dr = create_id2study_info(p, repo)
        d.update(dr)
    return d

DIGIT_PATTERN = re.compile(r'^\d')
def namespaced_get_alias(study_id):
    if DIGIT_PATTERN.match(study_id):
        if len(study_id) == 1:
            return [study_id, '0' + study_id, 'pg_' + study_id]
        elif len(study_id) == 2 and study_id[0] == '0':
            return [study_id, study_id[1], 'pg_' + study_id]
        return [study_id, 'pg_' + study_id]
    if study_id.startswith('pg_'):
        if len(study_id) == 4:
            return [study_id[-2:], study_id[-1], study_id]
        elif (len(study_id) == 5) and study_id[-2] == '0':
            return [study_id[-2:], study_id[-1], study_id]
        return [study_id[3:], study_id]
    return [study_id]

def diagnose_repo_study_id_convention(repo_dir):
    s = os.path.join(repo_dir, 'study')
    sl = os.listdir(s)
    for f in sl:
        if DIGIT_PATTERN.match(f):
            return {'convention': 'simple',
                    'fp_fn': get_filepath_for_simple_id,
                    'id2alias_list': lambda x: [x], }
    return {'convention': 'namespaced',
            'fp_fn': get_filepath_for_namespaced_id,
            'id2alias_list': namespaced_get_alias, }

_CACHE_REGION_CONFIGURED = False
_REGION = None
def _make_phylesystem_cache_region(**kwargs):
    '''Only intended to be called by the Phylesystem singleton.
    '''
    global _CACHE_REGION_CONFIGURED, _REGION
    if _CACHE_REGION_CONFIGURED:
        return _REGION
    _CACHE_REGION_CONFIGURED = True
    try:
        from dogpile.cache import make_region
    except:
        _LOG.debug('dogpile.cache not available')
        return
    region = None
    trial_key = 'test_key'
    trial_val = {'test_val': [4, 3]}
    trying_redis = True
    if trying_redis:
        try:
            a = {
                'host': 'localhost',
                'port': 6379,
                'db': 0, # default is 0
                'redis_expiration_time': 60*60*24*2,   # 2 days
                'distributed_lock': False #True if multiple processes will use redis
            }
            region = make_region().configure('dogpile.cache.redis', arguments=a)
            _LOG.debug('cache region set up with cache.redis.')
            _LOG.debug('testing redis caching...')
            region.set(trial_key, trial_val)
            assert trial_val == region.get(trial_key)
            _LOG.debug('redis caching works')
            region.delete(trial_key)
            _REGION = region
            return region
        except:
            _LOG.debug('redis cache set up failed.')
            region = None
    trying_file_dbm = False
    if trying_file_dbm:
        _LOG.debug('Going to try dogpile.cache.dbm ...')
        first_par = _get_phylesystem_parent(**kwargs)[0]
        cache_db_dir = os.path.split(first_par)[0]
        cache_db = os.path.join(cache_db_dir, 'phylesystem-cachefile.dbm')
        _LOG.debug('dogpile.cache region using "{}"'.format(cache_db))
        try:
            a = {'filename': cache_db}
            region = make_region().configure('dogpile.cache.dbm',
                                             expiration_time=36000,
                                             arguments=a)
            _LOG.debug('cache region set up with cache.dbm.')
            _LOG.debug('testing anydbm caching...')
            region.set(trial_key, trial_val)
            assert trial_val == region.get(trial_key)
            _LOG.debug('anydbm caching works')
            region.delete(trial_key)
            _REGION = region
            return region
        except:
            _LOG.debug('anydbm cache set up failed')
            _LOG.debug('exception in the configuration of the cache.')
    _LOG.debug('Phylesystem will not use caching')
    return None


