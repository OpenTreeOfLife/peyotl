# Simplified from peyotl.phylesystem.phylesystem_umbrella
# TODO:
#   - replace repo_nexml2json with repo_collection_version or similar?
#   - clobber all references to study prefix (eg, 'pg')
#   - add uniqueness test for collection_id instead
#   - replace collection_id with collection_id; this should be a unique
#     "path" string composed of '{ownerid}/{slugified-collection-name}'
#     EXAMPLES: 'jimallman/trees-about-bees'
#               'jimallman/other-interesting-stuff'
#               'kcranston/trees-about-bees'
#               'jimallman/trees-about-bees-2'
#   - refactor shard to base class, with generalized 'items'?
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
from peyotl.git_storage import ShardedDocStore
from peyotl.phylesystem.helper import get_repos, \
                                      _get_phylesystem_parent_with_source, \
                                      _make_phylesystem_cache_region
from peyotl.git_storage.sharded_doc_store import ShardedDocStore
#from peyotl.collection.collections_shard import TreeCollectionStoreShardProxy, \
#                                                 TreeCollectionStoreShard, \
#                                                 NotATreeCollectionStoreShardError
from peyotl.phylesystem.git_actions import GitAction
#from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
#                                             delete_study, \
#                                             validate_and_convert_nexson
#from peyotl.nexson_validation import ot_validate
from threading import Lock
import os
import re
COLLECTION_ID_PATTERN = re.compile(r'^[a-zA-Z]+_+[0-9]+$')
# TODO: allow simple slug-ified strings and slash separator (no whitespace!)
_LOG = get_logger(__name__)

def prefix_from_collection_path(collection_id):
    # The collection id is a sort of "path", e.g. '{userid}/{collection-name-as-slug}'
    #   EXAMPLES: 'jimallman/trees-about-bees', 'kcranston/interesting-trees-2'
    # Assume that the userid will work as a prefix, esp. by assigning all of a
    # user's collections to a single shard.for grouping in shards
    path_parts = collection_id.split('/')
    if len(path_parts) > 1:
        return path_parts[0]
    return 'anonymous'  # or perhaps None?

class TreeCollectionStoreProxy(ShardedDocStore):
    '''Proxy for interacting with external resources if given the configuration of a remote TreeCollectionStore
    '''
    def __init__(self, config):
        ShardedDocStore.__init__(self,
                                 prefix_from_doc_id=prefix_from_collection_path)
        for s in config.get('shards', []):
            self._shards.append(TreeCollectionStoreShardProxy(s))
        d = {}
        for s in self._shards:
            for k in s.collection_index.keys():
                if k in d:
                    raise KeyError('Collection "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._doc2shard_map = d

class _TreeCollectionStore(ShardedDocStore):
    '''Wrapper around a set of sharded git repos.
    '''
    def __init__(self,
                 repos_dict=None,
                 repos_par=None,
                 with_caching=True,
                 #repo_nexml2json=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=GitAction,
                 mirror_info=None,
                 #new_study_prefix=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        '''
        Repos can be found by passing in a `repos_par` (a directory that is the parent of the repos)
            or by trusting the `repos_dict` mapping of name to repo filepath.
        `with_caching` should be True for non-debugging uses.
        `repo_nexml2json` is optional. If specified all TreeCollectionStoreShard repos are assumed to store
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
        ShardedDocStore.__init__(self,
                                 prefix_from_doc_id=prefix_from_collection_path)
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
            try:
                shard = TreeCollectionStoreShard(repo_name,
                                         repo_filepath,
                                         git_ssh=git_ssh,
                                         pkey=pkey,
                                         #repo_nexml2json=repo_nexml2json,
                                         git_action_class=git_action_class,
                                         push_mirror_repo_path=push_mirror_repo_path,
                                         #new_study_prefix=new_study_prefix,
                                         infrastructure_commit_author=infrastructure_commit_author)
            except NotATreeCollectionStoreShardError as x:
                f = 'Git repo "{d}" found in your phylesystem parent, but it does not appear to be a phylesystem ' \
                    'shard. Please report this as a bug if this directory is supposed to be phylesystem shard. '\
                    'The triggering error message was:\n{e}'
                f = f.format(d=repo_filepath, e=str(x))
                _LOG.warn(f)
                continue
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
        self._prefix2shard = {}
        for shard in shards:
            for prefix in shard.known_prefixes:
                assert prefix not in self._prefix2shard # we don't currently support multiple shards with the same ID prefix scheme
                self._prefix2shard[prefix] = shard
        with self._index_lock:
            self._locked_refresh_collection_ids()
            # TODO: review; what does this do now?
        #self.repo_nexml2json = shards[-1].repo_nexml2json
        if with_caching:
            self._cache_region = _make_phylesystem_cache_region()
        else:
            self._cache_region = None
        self.git_action_class = git_action_class
        self._cache_hits = 0
    def _locked_refresh_collection_ids(self):
        '''Assumes that the caller has the _index_lock !
        '''
        d = {}
        for s in self._shards:
            for k in s.collection_index.keys():
                if k in d:
                    raise KeyError('Collection "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._doc2shard_map = d
        #self._new_study_prefix = self._growing_shard._new_study_prefix
        self._growing_shard._determine_next_collection_id()

    #    def _mint_new_collection_id(self):
    #        '''Checks out master branch of the shard as a side effect'''
    #        return self._growing_shard._mint_new_collection_id()
    #    @property
    #    def next_collection_id(self):
    #        return self._growing_shard.next_collection_id
    def has_collection(self, collection_id):
        with self._index_lock:
            return collection_id in self._doc2shard_map

    def create_git_action(self, collection_id):
        shard = self.get_shard(collection_id)
        return shard.create_git_action()

    def create_git_action_for_new_collection(self, new_collection_id=None):
        '''Checks out master branch of the shard as a side effect'''
        return self._growing_shard.create_git_action_for_new_collection(new_collection_id=new_collection_id)

    def get_filepath_for_collection(self, collection_id):
        ga = self.create_git_action(collection_id)
        return ga.path_for_collection(collection_id)

    def return_collection(self,
                          collection_id,
                          branch='master',
                          commit_sha=None,
                          return_WIP_map=False):
        ga = self.create_git_action(collection_id)
        with ga.lock():
            #_LOG.debug('pylesystem.return_collection({s}, {b}, {c}...)'.format(s=collection_id, b=branch, c=commit_sha))

            blob = ga.return_collection(collection_id,
                                        branch=branch,
                                        commit_sha=commit_sha,
                                        return_WIP_map=return_WIP_map)
            content = blob[0]
            if content is None:
                raise KeyError('Collection {} not found'.format(collection_id))
            nexson = anyjson.loads(blob[0])
            if return_WIP_map:
                return nexson, blob[1], blob[2]
            return nexson, blob[1]

    def get_blob_sha_for_collection_id(self, collection_id, head_sha):
        ga = self.create_git_action(collection_id)
        collpath = ga.path_for_collection(collection_id)
        return ga.get_blob_sha_for_file(collpath, head_sha)

    def get_version_history_for_collection_id(self, collection_id):
        ga = self.create_git_action(collection_id)
        collpath = ga.path_for_collection(collection_id)
        #from pprint import pprint
        #pprint('```````````````````````````````````')
        #pprint(ga.get_version_history_for_file(collpath))
        #pprint('```````````````````````````````````')
        return ga.get_version_history_for_file(collpath)

    def push_collection_to_remote(self, remote_name, collection_id=None):
        '''This will push the master branch to the remote named `remote_name`
        using the mirroring strategy to cut down on locking of the working repo.

        `collection_id` is used to determine which shard should be pushed.
        if `collection_id is None, all shards are pushed.
        '''
        if collection_id is None:
            ret = True
            #@TODO should spawn a thread of each shard...
            for shard in self._shards:
                if not shard.push_to_remote(remote_name):
                    ret = False
            return ret
        shard = self.get_shard(collection_id)
        return shard.push_to_remote(remote_name)

    def commit_and_try_merge2master(self,
                                    file_content,
                                    collection_id,
                                    auth_info,
                                    parent_sha,
                                    commit_msg='',
                                    merged_sha=None):
        git_action = self.create_git_action(collection_id)
        resp = commit_and_try_merge2master(git_action,
                                           file_content,
                                           collection_id,
                                           auth_info,
                                           parent_sha,
                                           commit_msg,
                                           merged_sha=merged_sha)
        if not resp['merge_needed']:
            self._collection_merged_hook(git_action, collection_id)
        return resp
    def annotate_and_write(self, #pylint: disable=R0201
                           git_data,
                           nexson,
                           collection_id,
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
        TODO: Reconsider this reasoning since add_validation_annotation doesn't
        apply to collections?
        '''
        return commit_and_try_merge2master(git_action=git_data,
                                           file_content=nexson,
                                           collection_id=collection_id,
                                           auth_info=auth_info,
                                           parent_sha=parent_sha,
                                           commit_msg=commit_msg,
                                           merged_sha=master_file_blob_included)
    def delete_collection(self, collection_id, auth_info, parent_sha, **kwargs):
        git_action = self.create_git_action(collection_id)
        ret = delete_collection(git_action, collection_id, auth_info, parent_sha, **kwargs)
        if not ret['merge_needed']:
            with self._index_lock:
                try:
                    _shard = self._doc2shard_map[collection_id]
                except KeyError:
                    pass
                else:
                    alias_list = _shard.id_alias_list_fn(collection_id)
                    for alias in alias_list:
                        try:
                            del self._doc2shard_map[alias]
                        except KeyError:
                            pass
                    _shard.delete_collection_from_index(collection_id)
        return ret

    def ingest_new_collection(self,
                              new_collection_json,
                              #repo_nexml2json,
                              auth_info,
                              new_collection_id=None):
        placeholder_added = False
        if new_collection_id is not None:
            #if new_collection_id.startswith(self._new_study_prefix):
            #    m = 'Study IDs with the "{}" prefix can only be automatically generated.'.format(self._new_study_prefix)
            #    raise ValueError(m)
            # TODO: Replace above with something similar?
            if not COLLECTION_ID_PATTERN.match(new_collection_id):
                raise ValueError("Collection ID does not match the expected pattern of '{userid}/{collection-name-as-slug}'")
            with self._index_lock:
                if new_collection_id in self._doc2shard_map:
                    raise ValueError('Collection ID is already in use!')
                self._doc2shard_map[new_collection_id] = None
                placeholder_added = True
        try:
            gd, new_collection_id = self.create_git_action_for_new_collection(new_collection_id=new_collection_id)
            try:
                nexml = new_collection_json['nexml']
                nexml['^ot:studyId'] = new_collection_id
                bundle = validate_and_convert_nexson(new_collection_json,
                                                     #repo_nexml2json,
                                                     allow_invalid=True)
                nexson, annotation, nexson_adaptor = bundle[0], bundle[1], bundle[3]
                r = self.annotate_and_write(git_data=gd,
                                            nexson=nexson,
                                            collection_id=new_collection_id,
                                            auth_info=auth_info,
                                            adaptor=nexson_adaptor,
                                            annotation=annotation,
                                            parent_sha=None,
                                            master_file_blob_included=None)
            except:
                self._growing_shard.delete_collection_from_index(new_collection_id)
                raise
        except:
            if placeholder_added:
                with self._index_lock:
                    if new_collection_id in self._doc2shard_map:
                        del self._doc2shard_map[new_collection_id]
            raise
        with self._index_lock:
            self._doc2shard_map[new_collection_id] = self._growing_shard
        return new_collection_id, r

    def iter_collection_objs(self, **kwargs):
        '''Generator that iterates over all stored collections and returns the
        collection object (deserialized from JSON) for each.
        Order is by shard, but arbitrary within shards.
        @TEMP not locked to prevent collection creation/deletion
        '''
        for shard in self._shards:
            for collection_id, blob in shard.iter_collection_objs(**kwargs):
                yield collection_id, blob

    def iter_collection_filepaths(self, **kwargs):
        '''Generator that iterates over all stored collections
        and returns the collection object (deserialized from JSON) for
        each collection.
        Order is by shard, but arbitrary within shards.
        @TEMP not locked to prevent collection creation/deletion
        '''
        for shard in self._shards:
            for collection_id, blob in shard.iter_collection_filepaths(**kwargs):
                yield collection_id, blob
    def pull(self, remote='origin', branch_name='master'):
        with self._index_lock:
            for shard in self._shards:
                shard.pull(remote=remote, branch_name=branch_name)
            self._locked_refresh_collection_ids()

    def report_configuration(self):
        out = StringIO()
        self.write_configuration(out)
        return out.getvalue()

    def write_configuration(self, out, secret_attrs=False):
        key_order = [#'repo_nexml2json',
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
        cd = {#'repo_nexml2json': self.repo_nexml2json,
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
    def get_changed_collections(self, ancestral_commit_sha, collection_ids_to_check=None):
        ret = None
        for i in self._shards:
            x = i.get_changed_collections(ancestral_commit_sha, collection_ids_to_check=collection_ids_to_check)
            if x is not False:
                ret = x
                break
        if ret is not None:
            return ret
        raise ValueError('No shard returned changed collections for the SHA')

_THE_TREE_COLLECTION_STORE = None
def TreeCollectionStore(repos_dict=None,
                repos_par=None,
                with_caching=True,
                #repo_nexml2json=None,
                git_ssh=None,
                pkey=None,
                git_action_class=GitAction,
                mirror_info=None,
                #new_study_prefix=None,
                infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>'):
    '''Factory function for a _TreeCollectionStore object.

    A wrapper around the _TreeCollectionStore class instantiation for
    the most common use case: a singleton _TreeCollectionStore.
    If you need distinct _TreeCollectionStore objects, you'll need to
    call that class directly.
    '''
    global _THE_TREE_COLLECTION_STORE
    if _THE_TREE_COLLECTION_STORE is None:
        _THE_TREE_COLLECTION_STORE = _TreeCollectionStore(repos_dict=repos_dict,
                                        repos_par=repos_par,
                                        with_caching=with_caching,
                                        #repo_nexml2json=repo_nexml2json,
                                        git_ssh=git_ssh,
                                        pkey=pkey,
                                        git_action_class=git_action_class,
                                        mirror_info=mirror_info,
                                        #new_study_prefix=new_study_prefix,
                                        infrastructure_commit_author=infrastructure_commit_author)
    return _THE_TREE_COLLECTION_STORE

