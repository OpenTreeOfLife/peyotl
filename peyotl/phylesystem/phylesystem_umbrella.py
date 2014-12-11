from peyotl.utility import get_logger
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
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
from peyotl.phylesystem.helper import get_repos, \
                                      _get_phylesystem_parent_with_source, \
                                      _make_phylesystem_cache_region

from peyotl.phylesystem.phylesystem_shard import PhylesystemShardProxy, PhylesystemShard
from peyotl.phylesystem.git_actions import GitAction
from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
                                             delete_study, \
                                             validate_and_convert_nexson
from peyotl.nexson_validation import ot_validate
from peyotl.nexson_validation._validation_base import NexsonAnnotationAdder, \
                                                      replace_same_agent_annotation
from threading import Lock
import os
import re
STUDY_ID_PATTERN = re.compile(r'^[a-zA-Z]+_+[0-9]+$')
_LOG = get_logger(__name__)
class _PhylesystemBase(object):
    '''Impl. of some basic functionality that a _Phylesystem or _PhylesystemProxy
    can provide.
    '''
    def __init__(self):
        self._index_lock = Lock()
        self._study2shard_map = {}
        self._shards = []
    #pylint: disable=E1101
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
        name, path_frag = self.get_repo_and_path_fragment(study_id)
        return 'https://raw.githubusercontent.com/OpenTreeOfLife/' + name + '/' + branch + '/' + path_frag
    get_external_url = get_public_url

    def get_study_ids(self, include_aliases=False):
        k = []
        for shard in self._shards:
            k.extend(shard.get_study_ids(include_aliases=include_aliases))
        return k

class PhylesystemProxy(_PhylesystemBase):
    '''Proxy for interacting with external resources if given the configuration of a remote Phylesystem
    '''
    def __init__(self, config):
        _PhylesystemBase.__init__(self)
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
                 mirror_info=None,
                 new_study_prefix=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
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
        _PhylesystemBase.__init__(self)
        if repos_dict is not None:
            self._filepath_args = 'repos_dict = {}'.format(repr(repos_dict))
        elif repos_par is not None:
            self._filepath_args = 'repos_par = {}'.format(repr(repos_par))
        else:
            fmt = '<No arg> default phylesystem_parent from {}'
            a = _get_phylesystem_parent_with_source(**kwargs)[1]
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
            repos_dict = get_repos(repos_par, **kwargs)
        shards = []
        repo_name_list = list(repos_dict.keys())
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
                                     push_mirror_repo_path=push_mirror_repo_path,
                                     new_study_prefix=new_study_prefix,
                                     infrastructure_commit_author=infrastructure_commit_author)
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
                        f = '"{}" is a protected remote name in the mirrored repo setup'
                        m = f.format(remote_name)
                        raise ValueError(m)
                    remote_url = remote_url_prefix + '/' + repo_name + '.git'
                    GitAction.add_remote(expected_push_mirror_repo_path, remote_name, remote_url)
                shard.push_mirror_repo_path = expected_push_mirror_repo_path
                for remote_name in push_mirror_remote_map.keys():
                    mga = shard._create_git_action_for_mirror() #pylint: disable=W0212
                    mga.fetch(remote_name)
            shards.append(shard)

        self._shards = shards
        self._growing_shard = shards[-1] # generalize with config...
        with self._index_lock:
            self._locked_refresh_study_ids()
        self.repo_nexml2json = shards[-1].repo_nexml2json
        if with_caching:
            self._cache_region = _make_phylesystem_cache_region()
        else:
            self._cache_region = None
        self.git_action_class = git_action_class
        self._cache_hits = 0
    def _locked_refresh_study_ids(self):
        '''Assumes that the caller has the _index_lock !
        '''
        d = {}
        for s in self._shards:
            for k in s.study_index.keys():
                if k in d:
                    raise KeyError('study "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._study2shard_map = d
        self._new_study_prefix = self._growing_shard._new_study_prefix
        self._growing_shard._determine_next_study_id()

    def _mint_new_study_id(self):
        '''Checks out master branch of the shard as a side effect'''
        return self._growing_shard._mint_new_study_id()
    @property
    def next_study_id(self):
        return self._growing_shard.next_study_id
    def has_study(self, study_id):
        with self._index_lock:
            return study_id in self._study2shard_map

    def get_shard(self, study_id):
        with self._index_lock:
            return self._study2shard_map[study_id]

    def create_git_action(self, study_id):
        shard = self.get_shard(study_id)
        return shard.create_git_action()

    def create_git_action_for_new_study(self, new_study_id=None):
        '''Checks out master branch of the shard as a side effect'''
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
            ret = True
            #@TODO should spawn a thread of each shard...
            for shard in self._shards:
                if not shard.push_to_remote(remote_name):
                    ret = False
            return ret
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
    def annotate_and_write(self, #pylint: disable=R0201
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
            if new_study_id.startswith(self._new_study_prefix):
                m = 'Study IDs with the "{}" prefix can only be automatically generated.'.format(self._new_study_prefix)
                raise ValueError(m)
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
                nexson, annotation, nexson_adaptor = bundle[0], bundle[1], bundle[3]
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
                with self._index_lock:
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
    def pull(self, remote='origin', branch_name='master'):
        with self._index_lock:
            for shard in self._shards:
                studies = shard.pull(remote=remote, branch_name=branch_name)
            self._locked_refresh_study_ids()

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
    def get_changed_studies(self, ancestral_commit_sha, study_ids_to_check=None):
        ret = None
        for i in self._shards:
            x = i.get_changed_studies(ancestral_commit_sha, study_ids_to_check=study_ids_to_check)
            if x is not False:
                ret = x
                break
        if ret is not None:
            return ret
        raise ValueError('No phylesystem shard returned changed studies for the SHA')

_THE_PHYLESYSTEM = None
def Phylesystem(repos_dict=None,
                repos_par=None,
                with_caching=True,
                repo_nexml2json=None,
                git_ssh=None,
                pkey=None,
                git_action_class=GitAction,
                mirror_info=None,
                new_study_prefix=None,
                infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>'):
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
                                        mirror_info=mirror_info,
                                        new_study_prefix=new_study_prefix,
                                        infrastructure_commit_author=infrastructure_commit_author)
    return _THE_PHYLESYSTEM

