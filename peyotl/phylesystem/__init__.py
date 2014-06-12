#!/usr/bin/env python
'''Utilities for dealing with local filesystem
copies of the phylesystem repositories.
'''
from peyotl.utility import get_config, expand_path, get_logger
from cStringIO import StringIO
import json
try:
    import anyjson
except:
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads
try:
    from dogpile.cache.api import NO_VALUE
except:
    pass #caching is optional
from peyotl.phylesystem.git_actions import GitAction, \
                                           get_filepath_for_namespaced_id, \
                                           get_filepath_for_simple_id
from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
                                             delete_study, \
                                             validate_and_convert_nexson
from peyotl.nexson_syntax import detect_nexson_version
from peyotl.nexson_validation import ot_validate
from peyotl.nexson_validation._validation_base import NexsonAnnotationAdder, \
                                                      replace_same_agent_annotation
import codecs
import os
import re
from threading import Lock
_LOG = get_logger(__name__)
_study_index_lock = Lock()
_study_index = None

STUDY_ID_PATTERN = re.compile(r'^[a-zA-Z]+_+[0-9]+$')
def _get_phylesystem_parent_with_source():
    src = 'environment'
    if 'PHYLESYSTEM_PARENT' in os.environ:
        phylesystem_parent = os.environ.get('PHYLESYSTEM_PARENT')
    else:
        try:
            phylesystem_parent = expand_path(get_config('phylesystem', 'parent'))
            src = 'configfile'
        except:
            raise ValueError('No [phylesystem] "parent" specified in config or environmental variables')
    x = phylesystem_parent.split(':') #TEMP hardcoded assumption that : does not occur in a path name
    return x, src

def _get_phylesystem_parent():
    return _get_phylesystem_parent_with_source()[0]


def get_repos(par_list=None):
    '''Returns a dictionary of name -> filepath
    `name` is the repo name based on the dir name (not the get repo). It is not
        terribly useful, but it is nice to have so that any mirrored repo directory can
        use the same naming convention.
    `filepath` will be the full path to the repo directory (it will end in `name`)
    '''
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
                # if file is in more than one place it gets over written.
                #TODO EJM Needs work
                study_id = filename[:-5]
                d[study_id] = (tag, root, os.path.join(root, filename))
    return d

def _initialize_study_index(repos_par=None):
    d = {} # Key is study id, value is repo,dir tuple
    repos = get_repos(repos_par)
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
                    'id2alias_list': lambda x: [x]
            }
    return {'convention': 'namespaced',
            'fp_fn': get_filepath_for_namespaced_id,
            'id2alias_list': namespaced_get_alias,
    }

class PhylesystemShardBase(object):
    def get_rel_path_fragment(self, study_id):
        '''For `study_id` returns the path from the
        repo to the study file. This is useful because
        (if you know the remote), it lets you construct the full path.
        '''
        with self._index_lock:
            r = self._study_index[study_id]
        fp = r[-1]
        return fp[(len(self.path) + 1):] # "+ 1" to remove the /
    def get_study_index(self):
        return self._study_index
    study_index = property(get_study_index)
    def get_study_ids(self, include_aliases=False):
        with self._index_lock:
            k = self._study_index.keys()
        if self.has_aliases and (not include_aliases):
            x = []
            for i in k:
                if DIGIT_PATTERN.match(i) or ((len(i) > 1) and (i[-2] == '_')):
                    pass
                else:
                    x.append(i)
            return x
        return k

class PhylesystemShard(PhylesystemShardBase):
    '''Wrapper around a git repos holding nexson studies'''
    def __init__(self,
                 name,
                 path,
                 repo_nexml2json=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=GitAction,
                 push_mirror_repo_path=None):
        self._index_lock = Lock()
        self._ga_class = git_action_class
        self.git_ssh = git_ssh
        self.pkey = pkey
        self.name = name
        path = os.path.abspath(path)
        dot_git = os.path.join(path, '.git')
        study_dir = os.path.join(path, 'study')
        self.push_mirror_repo_path = push_mirror_repo_path
        if not os.path.isdir(path):
            raise ValueError('"{p}" is not a directory'.format(p=path))
        if not os.path.isdir(dot_git):
            raise ValueError('"{p}" is not a directory'.format(p=dot_git))
        if not os.path.isdir(study_dir):
            raise ValueError('"{p}" is not a directory'.format(p=study_dir))
        d = create_id2study_info(study_dir, name)
        rc_dict = diagnose_repo_study_id_convention(path)
        self.filepath_for_study_id_fn = rc_dict['fp_fn']
        self.id_alias_list_fn = rc_dict['id2alias_list']
        if rc_dict['convention'] != 'simple':
            a = {}
            for k, v in d.items():
                alias_list = self.id_alias_list_fn(k)
                for alias in alias_list:
                    a[alias] = v
            d = a
            self.has_aliases = True
        else:
            self.has_aliases = False

        self._study_index = d
        self.path = path
        self.parent_path = os.path.split(path)[0] + '/'
        self.git_dir = dot_git
        self.study_dir = study_dir
        if repo_nexml2json is None:
            try:
                repo_nexml2json = get_config('phylesystem', 'repo_nexml2json')
            except:
                pass
            if repo_nexml2json == None:
                repo_nexml2json = self.diagnose_repo_nexml2json()
        self.repo_nexml2json = repo_nexml2json
        self._next_study_id = None
        self._study_counter_lock = None

    def register_new_study(self, study_id):
        pass

    def delete_study_from_index(self, study_id):
        alias_list = self.id_alias_list_fn(study_id)
        with self._index_lock:
            for i in alias_list:
                try:
                    del self._study_index[i]
                except:
                    pass

    def determine_next_study_id(self, prefix='ot_'):
        "Return the numeric part of the newest study_id"
        if self._study_counter_lock is None:
            self._study_counter_lock = Lock()
        n = 0
        lp = len(prefix)
        with self._index_lock:
            for k in self._study_index.keys():
                if k.startswith(prefix):
                    try:
                        pn = int(k[lp:])
                        if pn > n:
                            n = pn
                    except:
                        pass
        with self._study_counter_lock:
            self._next_study_id = 1 + n

    def diagnose_repo_nexml2json(self):
        with self._index_lock:
            fp = self.study_index.values()[0][2]
        _LOG.debug('diagnose_repo_nexml2json with fp={}'.format(fp))
        with codecs.open(fp, mode='rU', encoding='utf-8') as fo:
            fj = json.load(fo)
            return detect_nexson_version(fj)

    def create_git_action(self):
        return self._ga_class(repo=self.path,
                              git_ssh=self.git_ssh,
                              pkey=self.pkey,
                              path_for_study_fn=self.filepath_for_study_id_fn)

    def create_git_action_for_new_study(self, new_study_id=None):
        ga = self.create_git_action()
        if new_study_id is None:
            # studies created by the OpenTree API start with ot_,
            # so they don't conflict with new study id's from other sources
            with self._study_counter_lock:
                c = self._next_study_id
                self._next_study_id = 1 + c
            #@TODO. This form of incrementing assumes that
            #   this codebase is the only service minting
            #   new study IDs!
            new_study_id = "ot_{c:d}".format(c=c)
        fp = ga.path_for_study(new_study_id)
        with self._index_lock:
            self._study_index[new_study_id] = (self.name, self.study_dir, fp)
        return ga, new_study_id

    def _create_git_action_for_mirror(self):
        mirror_ga = self._ga_class(repo=self.push_mirror_repo_path,
                                   git_ssh=self.git_ssh,
                                   pkey=self.pkey,
                                   path_for_study_fn=self.filepath_for_study_id_fn)
        return mirror_ga

    def push_to_remote(self, remote_name):
        if self.push_mirror_repo_path is None:
            raise RuntimeError('This PhylesystemShard has no push mirror, so it cannot push to a remote.')
        working_ga = self.create_git_action()
        mirror_ga = self._create_git_action_for_mirror()
        with mirror_ga.lock():
            with working_ga.lock():
                mirror_ga.fetch(remote='origin')
            mirror_ga.merge('origin/master', destination='master')
            mirror_ga.push(branch='master',
                           remote=remote_name)
        return True

    def _is_alias(self, study_id):
        alias_list = self.id_alias_list_fn(study_id)
        if len(alias_list) > 1:
            ml = max([len(i) for i in alias_list])
            if ml > len(study_id):
                return True
        return False

    def iter_study_filepaths(self, **kwargs):
        '''Returns a pair: (study_id, absolute filepath of study file)
        for each study in this repository.
        Order is arbitrary.
        '''
        with self._index_lock:
            for study_id, info in self._study_index.items():
                if not self._is_alias(study_id):
                    yield study_id, info[-1]

    def iter_study_objs(self, **kwargs):
        '''Returns a pair: (study_id, nexson_blob)
        for each study in this repository.
        Order is arbitrary.
        '''
        for study_id, fp in self.iter_study_filepaths(**kwargs):
            if not self._is_alias(study_id):
                with codecs.open(fp, 'rU', 'utf-8') as fo:
                    try:
                        nex_obj = anyjson.loads(fo.read())
                        yield (study_id, nex_obj)
                    except Exception:
                        pass

    def write_configuration(self, out, secret_attrs=False):
        key_order = ['name', 'path', 'git_dir', 'study_dir', 'repo_nexml2json',
                    'git_ssh', 'pkey', 'has_aliases', '_next_study_id',
                    'number of studies']
        cd = self.get_configuration_dict(secret_attrs=secret_attrs)
        for k in key_order:
            if k in cd:
                out.write('  {} = {}'.format(k, cd[k]))
        out.write('  studies in alias groups:\n')
        for o in cd['studies']:
            out.write('    {} ==> {}\n'.format(o['keys'], o['relpath']))

    def get_configuration_dict(self, secret_attrs=False):
        rd = {'name': self.name,
              'path': self.path,
              'git_dir': self.git_dir,
              'repo_nexml2json': self.repo_nexml2json,
              'study_dir': self.study_dir,
              'git_ssh': self.git_ssh,
              }
        if self._next_study_id is not None:
            rd['_next_study_id'] = self._next_study_id,
        if secret_attrs:
            rd['pkey'] = self.pkey
        with self._index_lock:
            si = self._study_index
        r = _invert_dict_list_val(si)
        key_list = r.keys()
        rd['number of studies'] = len(key_list)
        key_list.sort()
        m = []
        for k in key_list:
            v = r[k]
            fp = k[2]
            assert fp.startswith(self.study_dir)
            rp = fp[len(self.study_dir) + 1:]
            m.append({'keys': v, 'relpath': rp})
        rd['studies'] = m
        return rd
    def get_branch_list(self):
        ga = self.create_git_action()
        return ga.get_branch_list()
def _invert_dict_list_val(d):
    o = {}
    for k, v in d.items():
        o.setdefault(v, []).append(k)
    for v in o.values():
        v.sort()
    return o
_CACHE_REGION_CONFIGURED = False
_REGION = None
def _make_phylesystem_cache_region():
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
            _LOG.exception('redis cache set up failed.')
            region = None
    trying_file_dbm = False
    if trying_file_dbm:
        _LOG.debug('Going to try dogpile.cache.dbm ...')
        first_par = _get_phylesystem_parent()[0]
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
            _LOG.exception('anydbm cache set up failed')
            _LOG.debug('exception in the configuration of the cache.')
    _LOG.debug('Phylesystem will not use caching')
    return None


class _PhylesystemBase(object):
    '''Impl. of some basic functionality that a _Phylesystem or _PhylesystemProxy
    can provide.
    '''
    def get_repo_and_path_fragment(self, study_id):
        '''For `study_id` returns a list of:
            [0] the repo name and,
            [1] the path from the repo to the study file.
        This is useful because
        (if you know the remote), it lets you construct the full path.
        '''
        with self._index_lock:
            shard = self._study2shard_map[study_id]
        return shard.name, shard.get_rel_path_fragment(study_id)

    def get_public_url(self, study_id, branch='master'):
        '''Returns a GitHub URL for the
        '''
        #@TEMP, TODO. should look in the remote to find this. But then it can be tough to determine
        #       which (if any) remotes are publicly visible... hmmmm
        name, path_frag = self.get_repo_and_path_fragment(study_id)
        return 'https://raw.githubusercontent.com/OpenTreeOfLife/' + name + '/' + branch + '/' + path_frag
    get_external_url = get_public_url

    def get_study_ids(self, include_aliases=False):
        k = []
        for shard in self._shards:
            k.extend(shard.get_study_ids(include_aliases=include_aliases))
        return k

class PhylesystemShardProxy(PhylesystemShardBase):
    '''Proxy for interacting with external resources if given the
    configuration of a remote Phylesystem
    '''
    def __init__(self, config):
        self._index_lock = Lock() #TODO should invent a fake lock for the proxies
        self.name = config['name']
        self.repo_nexml2json = config['repo_nexml2json']
        self.path = ' ' # mimics place of the abspath of repo in path -> relpath mapping
        self.has_aliases = False
        d = {}
        for study in config['studies']:
            kl = study['keys']
            if len(kl) > 1:
                self.has_aliases = True
            for k in study['keys']:
                d[k] = (self.name, self.path, self.path + '/study/' + study['relpath'])
        self._study_index = d

class PhylesystemProxy(_PhylesystemBase):
    '''Proxy for interacting with external resources if given the
    configuration of a remote Phylesystem
    '''
    def __init__(self, config):
        self._index_lock = Lock() #TODO should invent a fake lock for the proxies
        self.repo_nexml2json = config['repo_nexml2json']
        self._shards = []
        for s in config.get('shards', []):
            self._shards.append(PhylesystemShardProxy(s))
        d = {}
        for s in self._shards:
            for k in s.study_index.keys():
                if k in d:
                    raise KeyError('study "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._study2shard_map = d

class _Phylesystem(_PhylesystemBase):
    '''Wrapper around a set of sharded git repos.
    '''
    def __init__(self,
                 repos_dict=None,
                 repos_par=None,
                 with_caching=True,
                 repo_nexml2json=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=GitAction,
                 mirror_info=None):
        '''
        Repos can be found by passing in a `repos_par` (a directory that is the parent of the repos)
            or by trusting the `repos_dict` mapping of name to repo filepath.
        `with_caching` should be True for non-debugging uses.
        `repo_nexml2json` is optional. If specified all PhylesystemShard repos are assumed to store
            files of this version of nexson syntax.
        `git_ssh` is the path of an executable for git-ssh operations.
        `pkey` is the PKEY that has to be in the env for remote, authenticated operations to work
        `git_action_class` is a subclass of GitAction to use. the __init__ syntax must be compatible
            with GitAction
        If you want to use a mirrors of the repo for pushes or pulls, send in a `mirror_info` dict:
            mirror_info['push'] and mirror_info['pull'] should be dicts with the following keys:
            'parent_dir' - the parent directory of the mirrored repos
            'remote_map' - a dictionary of remote name to prefix (the repo name + '.git' will be
                appended to create the URL for pushing).
        '''
        if repos_dict is not None:
            self._filepath_args = 'repos_dict = {}'.format(repr(repos_dict))
        elif repos_par is not None:
            self._filepath_args = 'repos_par = {}'.format(repr(repos_par))
        else:
            fmt = '<No arg> default phylesystem_parent from {}'
            a = _get_phylesystem_parent_with_source()[1]
            self._filepath_args = fmt.format(a)
        push_mirror_repos_par = None
        push_mirror_remote_map = {}
        if mirror_info:
            push_mirror_info = mirror_info.get('push', {})
            if push_mirror_info:
                push_mirror_repos_par = push_mirror_info['parent_dir']
                push_mirror_remote_map = push_mirror_info.get('remote_map', {})
                if push_mirror_repos_par:
                    if not os.path.exists(push_mirror_repos_par):
                        os.makedirs(push_mirror_repos_par)
                    if not os.path.isdir(push_mirror_repos_par):
                        e_fmt = 'Specified push_mirror_repos_par, "{}", is not a directory'
                        e = e_fmt.format(push_mirror_repos_par)
                        raise ValueError(e)
        if repos_dict is None:
            repos_dict = get_repos(repos_par)
        shards = []
        repo_name_list = repos_dict.keys()
        repo_name_list.sort()
        for repo_name in repo_name_list:
            repo_filepath = repos_dict[repo_name]
            push_mirror_repo_path = None
            if push_mirror_repos_par:
                expected_push_mirror_repo_path = os.path.join(push_mirror_repos_par, repo_name)
                if os.path.isdir(expected_push_mirror_repo_path):
                    push_mirror_repo_path = expected_push_mirror_repo_path
            shard = PhylesystemShard(repo_name,
                                     repo_filepath,
                                     git_ssh=git_ssh,
                                     pkey=pkey,
                                     repo_nexml2json=repo_nexml2json,
                                     git_action_class=git_action_class,
                                     push_mirror_repo_path=push_mirror_repo_path)
            # if the mirror does not exist, clone it...
            if push_mirror_repos_par and (push_mirror_repo_path is None):
                GitAction.clone_repo(push_mirror_repos_par,
                                     repo_name,
                                     repo_filepath)
                if not os.path.isdir(expected_push_mirror_repo_path):
                    e_msg = 'git clone in mirror bootstrapping did not produce a directory at {}'
                    e = e_msg.format(expected_push_mirror_repo_path)
                    raise ValueError(e)
                for remote_name, remote_url_prefix in push_mirror_remote_map.items():
                    if remote_name in ['origin', 'originssh']:
                        raise ValueError('"{}" is a protected remote name in the mirrored repo setup'.format(remote_name))
                    remote_url = remote_url_prefix + '/' + repo_name + '.git'
                    GitAction.add_remote(expected_push_mirror_repo_path, remote_name, remote_url)
                shard.push_mirror_repo_path = expected_push_mirror_repo_path
                for remote_name in push_mirror_remote_map.keys():
                    mga = shard._create_git_action_for_mirror()
                    mga.fetch(remote_name)
            shards.append(shard)


        d = {}
        for s in shards:
            for k in s.study_index.keys():
                if k in d:
                    raise KeyError('study "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._study2shard_map = d
        self._index_lock = Lock()
        self._shards = shards
        self._growing_shard = shards[-1] # generalize with config...
        self._growing_shard.determine_next_study_id()
        self.repo_nexml2json = shards[-1].repo_nexml2json
        if with_caching:
            self._cache_region = _make_phylesystem_cache_region()
        else:
            self._cache_region = None
        self.git_action_class = git_action_class
        self._cache_hits = 0

    def get_shard(self, study_id):
        with self._index_lock:
            return self._study2shard_map[study_id]

    def create_git_action(self, study_id):
        shard = self.get_shard(study_id)
        return shard.create_git_action()

    def create_git_action_for_new_study(self, new_study_id=None):
        return self._growing_shard.create_git_action_for_new_study(new_study_id=new_study_id)

    def add_validation_annotation(self, study_obj, sha):
        need_to_cache = False
        adaptor = None
        if self._cache_region is not None:
            key = 'v' + sha
            annot_event = self._cache_region.get(key, ignore_expiration=True)
            if annot_event != NO_VALUE:
                _LOG.debug('cache hit for ' + key)
                adaptor = NexsonAnnotationAdder()
                self._cache_hits += 1
            else:
                _LOG.debug('cache miss for ' + key)
                need_to_cache = True

        if adaptor is None:
            bundle = ot_validate(study_obj)
            annotation = bundle[0]
            annot_event = annotation['annotationEvent']
            #del annot_event['@dateCreated'] #TEMP
            #del annot_event['@id'] #TEMP
            adaptor = bundle[2]
        replace_same_agent_annotation(study_obj, annot_event)
        if need_to_cache:
            self._cache_region.set(key, annot_event)
            _LOG.debug('set cache for ' + key)

        return annot_event

    def get_filepath_for_study(self, study_id):
        ga = self.create_git_action(study_id)
        return ga.path_for_study(study_id)

    def return_study(self,
                     study_id,
                     branch='master',
                     commit_sha=None,
                     return_WIP_map=False):
        ga = self.create_git_action(study_id)
        with ga.lock():
            #_LOG.debug('pylesystem.return_study({s}, {b}, {c}...)'.format(s=study_id, b=branch, c=commit_sha))

            blob = ga.return_study(study_id,
                                   branch=branch,
                                   commit_sha=commit_sha,
                                   return_WIP_map=return_WIP_map)
            nexson = anyjson.loads(blob[0])
            if return_WIP_map:
                return nexson, blob[1], blob[2]
            return nexson, blob[1]

    def get_blob_sha_for_study_id(self, study_id, head_sha):
        ga = self.create_git_action(study_id)
        studypath = ga.path_for_study(study_id)
        return ga.get_blob_sha_for_file(studypath, head_sha)

    def get_version_history_for_study_id(self, study_id):
        ga = self.create_git_action(study_id)
        studypath = ga.path_for_study(study_id)
        #from pprint import pprint
        #pprint('```````````````````````````````````')
        #pprint(ga.get_version_history_for_file(studypath))
        #pprint('```````````````````````````````````')
        return ga.get_version_history_for_file(studypath)

    def push_study_to_remote(self, remote_name, study_id=None):
        '''This will push the master branch to the remote named `remote_name`
        using the mirroring strategy to cut down on locking of the working repo.

        `study_id` is used to determine which shard should be pushed.
        if `study_id is None, all shards are pushed.
        '''
        if study_id is None:
            #@TODO should spawn a thread of each shard...
            for shard in self._shards:
                if not shard.push_to_remote(remote_name):
                    return False
            return True
        shard = self.get_shard(study_id)
        return shard.push_to_remote(remote_name)

    def commit_and_try_merge2master(self,
                                    file_content,
                                    study_id,
                                    auth_info,
                                    parent_sha,
                                    commit_msg='',
                                    merged_sha=None):
        git_action = self.create_git_action(study_id)
        return commit_and_try_merge2master(git_action,
                                           file_content,
                                           study_id,
                                           auth_info,
                                           parent_sha,
                                           commit_msg,
                                           merged_sha=merged_sha)
    def annotate_and_write(self,
                           git_data,
                           nexson,
                           study_id,
                           auth_info,
                           adaptor,
                           annotation,
                           parent_sha,
                           commit_msg='',
                           master_file_blob_included=None):
        '''
        This is the heart of the api's __finish_write_verb
        It was moved to phylesystem to make it easier to coordinate it
            with the caching decisions. We have been debating whether
            to cache @id and @dateCreated attributes for the annotations
            or cache the whole annotation. Since these decisions are in
            add_validation_annotation (above), it is easier to have
            that decision and the add_or_replace_annotation call in the
            same repo.
        '''
        adaptor.add_or_replace_annotation(nexson,
                                          annotation['annotationEvent'],
                                          annotation['agent'],
                                          add_agent_only=True)
        return commit_and_try_merge2master(git_action=git_data,
                                           file_content=nexson,
                                           study_id=study_id,
                                           auth_info=auth_info,
                                           parent_sha=parent_sha,
                                           commit_msg=commit_msg,
                                           merged_sha=master_file_blob_included)
    def delete_study(self, study_id, auth_info, parent_sha):
        git_action = self.create_git_action(study_id)
        ret = delete_study(git_action, study_id, auth_info, parent_sha)
        with self._index_lock:
            _shard = self._study2shard_map[study_id]
            alias_list = _shard.id_alias_list_fn(study_id)
            for alias in alias_list:
                del self._study2shard_map[alias]
            _shard.delete_study_from_index(study_id)
        return ret

    def ingest_new_study(self,
                         new_study_nexson,
                         repo_nexml2json,
                         auth_info,
                         new_study_id=None):
        placeholder_added = False
        if new_study_id is not None:
            if new_study_id.startswith('ot_'):
                raise ValueError('Study IDs with the "ot_" prefix can only be automatically generated.')
            if not STUDY_ID_PATTERN.match(new_study_id):
                raise ValueError('Study ID does not match the expected pattern of alphabeticprefix_numericsuffix')
            with self._index_lock:
                if new_study_id in self._study2shard_map:
                    raise ValueError('Study ID is already in use!')
                self._study2shard_map[new_study_id] = None
                placeholder_added = True
        try:
            gd, new_study_id = self.create_git_action_for_new_study(new_study_id=new_study_id)
            try:
                nexml = new_study_nexson['nexml']
                nexml['^ot:studyId'] = new_study_id
                bundle = validate_and_convert_nexson(new_study_nexson,
                                                     repo_nexml2json,
                                                     allow_invalid=True)
                nexson, annotation, validation_log, nexson_adaptor = bundle
                r = self.annotate_and_write(git_data=gd,
                                            nexson=nexson,
                                            study_id=new_study_id,
                                            auth_info=auth_info,
                                            adaptor=nexson_adaptor,
                                            annotation=annotation,
                                            parent_sha=None,
                                            master_file_blob_included=None)
            except:
                self._growing_shard.delete_study_from_index(new_study_id)
                raise
        except:
            if placeholder_added:
                del self._study2shard_map[new_study_id]
            raise
        with self._index_lock:
            self._study2shard_map[new_study_id] = self._growing_shard
        return new_study_id, r

    def iter_study_objs(self, **kwargs):
        '''Generator that iterates over all detected phylesystem studies.
        and returns the study object (deserialized from nexson) for
        each study.
        Order is by shard, but arbitrary within shards.
        @TEMP not locked to prevent study creation/deletion
        '''
        for shard in self._shards:
            for study_id, blob in shard.iter_study_objs(**kwargs):
                yield study_id, blob

    def iter_study_filepaths(self, **kwargs):
        '''Generator that iterates over all detected phylesystem studies.
        and returns the study object (deserialized from nexson) for
        each study.
        Order is by shard, but arbitrary within shards.
        @TEMP not locked to prevent study creation/deletion
        '''
        for shard in self._shards:
            for study_id, blob in shard.iter_study_filepaths(**kwargs):
                yield study_id, blob

    def report_configuration(self):
        out = StringIO()
        self.write_configuration(out)
        return out.getvalue()

    def write_configuration(self, out, secret_attrs=False):
        key_order = ['repo_nexml2json',
                     'number_of_shards',
                     'initialization',]
        cd = self.get_configuration_dict(secret_attrs=secret_attrs)
        for k in key_order:
            if k in cd:
                out.write('  {} = {}'.format(k, cd[k]))
        for n, shard in enumerate(self._shards):
            out.write('Shard {}:\n'.format(n))
            shard.write_configuration(out)
    def get_configuration_dict(self, secret_attrs=False):
        cd = {'repo_nexml2json': self.repo_nexml2json,
              'number_of_shards': len(self._shards),
              'initialization': self._filepath_args}
        cd['shards'] = []
        for i in self._shards:
            cd['shards'].append(i.get_configuration_dict(secret_attrs=secret_attrs))
        return cd
    def get_branch_list(self):
        a = []
        for i in self._shards:
            a.extend(i.get_branch_list())
        return a
        
_THE_PHYLESYSTEM = None
def Phylesystem(repos_dict=None,
                repos_par=None,
                with_caching=True,
                repo_nexml2json=None,
                git_ssh=None,
                pkey=None,
                git_action_class=GitAction,
                mirror_info=None):
    '''Factory function for a _Phylesystem object.

    A wrapper around the _Phylesystem class instantiation for
    the most common use case: a singleton _Phylesystem.
    If you need distinct _Phylesystem objects, you'll need to
    call that class directly.
    '''
    global _THE_PHYLESYSTEM
    if _THE_PHYLESYSTEM is None:
        _THE_PHYLESYSTEM = _Phylesystem(repos_dict=repos_dict,
                                        repos_par=repos_par,
                                        with_caching=with_caching,
                                        repo_nexml2json=repo_nexml2json,
                                        git_ssh=git_ssh,
                                        pkey=pkey,
                                        git_action_class=git_action_class,
                                        mirror_info=mirror_info)
    return _THE_PHYLESYSTEM

# Cache keys:
# v+SHA = annotation event from validation
