"""Base class for "type-aware" (sharded) document storage. This goes beyond simple subclasses 
like PhylsystemProxy by introducing more business rules and differences between document types
in the store (eg, Nexson studies in Phylesystem, tree collections in TreeCollectionStore)."""
import os
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
try:
    import anyjson
except:
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads
from peyotl.git_storage import ShardedDocStore
from peyotl.git_storage.git_shard import FailedShardCreationError

from peyotl.utility import pretty_timestamp, get_logger
_LOG = get_logger(__name__)

class TypeAwareDocStore(ShardedDocStore):
    def __init__(self, 
                 prefix_from_doc_id,
                 repos_dict=None,
                 repos_par=None,
                 with_caching=True,
                 assumed_doc_version=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=None, # requires a *type-specific* GitActionBase subclass
                 git_shard_class=None, # requires a *type-specific* GitShard subclass
                 mirror_info=None,
                 new_doc_prefix=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        '''
        Repos can be found by passing in a `repos_par` (a directory that is the parent of the repos)
            or by trusting the `repos_dict` mapping of name to repo filepath.
        `prefix_from_doc_id` should be a type-specific method defined in the subclass
        `with_caching` should be True for non-debugging uses.
        `assumed_doc_version` is optional. If specified all shard repos are assumed to store
            files of this version of the primary document syntax.
        `git_ssh` is the path of an executable for git-ssh operations.
        `pkey` is the PKEY that has to be in the env for remote, authenticated operations to work
        `git_action_class` is a subclass of GitActionBase to use. the __init__ syntax must be compatible
            with PhylesystemGitAction
        If you want to use a mirrors of the repo for pushes or pulls, send in a `mirror_info` dict:
            mirror_info['push'] and mirror_info['pull'] should be dicts with the following keys:
            'parent_dir' - the parent directory of the mirrored repos
            'remote_map' - a dictionary of remote name to prefix (the repo name + '.git' will be
                appended to create the URL for pushing).
        '''
        from peyotl.phylesystem.helper import get_repos, \
                                              _get_phylesystem_parent_with_source
        ShardedDocStore.__init__(self,
                                 prefix_from_doc_id=prefix_from_doc_id)
        self.assumed_doc_version = assumed_doc_version
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
                # assumes uniform __init__ arguments for all GitShard subclasses
                shard = git_shard_class(repo_name,
                                        repo_filepath,
                                        assumed_doc_version,
                                        git_ssh,
                                        pkey,
                                        git_action_class,
                                        push_mirror_repo_path,
                                        new_doc_prefix,
                                        infrastructure_commit_author)
            except FailedShardCreationError as x:
                f = 'Git repo "{d}" found in your docstore parent, but it does not appear to be a {c}' \
                    'shard. Please report this as a bug if this directory is supposed to be this type of shard. '\
                    'The triggering error message was:\n{e}'
                f = f.format(d=repo_filepath, c=git_shard_class, e=str(x))
                _LOG.warn(f)
                continue
            # if the mirror does not exist, clone it...
            if push_mirror_repos_par and (push_mirror_repo_path is None):
                from peyotl.git_storage import GitActionBase
                GitActionBase.clone_repo(push_mirror_repos_par,
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
                    GitActionBase.add_remote(expected_push_mirror_repo_path, remote_name, remote_url)
                shard.push_mirror_repo_path = expected_push_mirror_repo_path
                for remote_name in push_mirror_remote_map.keys():
                    mga = shard._create_git_action_for_mirror() #pylint: disable=W0212
                    mga.fetch(remote_name)
            shards.append(shard)

        self._shards = shards
        if len(shards) < 1:
            self._growing_shard = None
        else:
            self._growing_shard = shards[-1] # generalize with config...
        self._prefix2shard = {}
        for shard in shards:
            for prefix in shard.known_prefixes:
                assert prefix not in self._prefix2shard # we don't currently support multiple shards with the same ID prefix scheme
                self._prefix2shard[prefix] = shard
        with self._index_lock:
            self._locked_refresh_doc_ids()
        if self.assumed_doc_version is None:
            # if no version was specified, try to pick it up from a shard's contents (using auto-detect)
            if self._growing_shard:
                self.assumed_doc_version = self._growing_shard.assumed_doc_version
        self.git_action_class = git_action_class
    def _locked_refresh_doc_ids(self):
        '''Assumes that the caller has the _index_lock !
        '''
        d = {}
        for s in self._shards:
            for k in s.doc_index.keys():
                if k in d:
                    raise KeyError('doc "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._doc2shard_map = d

    def has_doc(self, doc_id):
        with self._index_lock:
            return doc_id in self._doc2shard_map

    def create_git_action(self, doc_id):
        shard = self.get_shard(doc_id)
        if shard is None:
            shard = self._growing_shard
        assert shard is not None
        return shard.create_git_action()

    def get_filepath_for_doc(self, doc_id):
        ga = self.create_git_action(doc_id)
        return ga.path_for_doc(doc_id)

    def return_doc(self,
                   doc_id,
                   branch='master',
                   commit_sha=None,
                   return_WIP_map=False):
        ga = self.create_git_action(doc_id)
        with ga.lock():
            #_LOG.debug('pylesystem.return_doc({s}, {b}, {c}...)'.format(s=doc_id, b=branch, c=commit_sha))

            blob = ga.return_document(doc_id,
                                      branch=branch,
                                      commit_sha=commit_sha,
                                      return_WIP_map=return_WIP_map)
            content = blob[0]
            if content is None:
                raise KeyError('Document {} not found'.format(doc_id))
            nexson = anyjson.loads(blob[0])
            if return_WIP_map:
                return nexson, blob[1], blob[2]
            return nexson, blob[1]

    def get_blob_sha_for_doc_id(self, doc_id, head_sha):
        ga = self.create_git_action(doc_id)
        docpath = ga.path_for_doc(doc_id)
        return ga.get_blob_sha_for_file(docpath, head_sha)

    def get_version_history_for_doc_id(self, doc_id):
        ga = self.create_git_action(doc_id)
        docpath = ga.path_for_doc(doc_id)
        #from pprint import pprint
        #pprint('```````````````````````````````````')
        #pprint(ga.get_version_history_for_file(docpath))
        #pprint('```````````````````````````````````')
        return ga.get_version_history_for_file(docpath)

    def push_doc_to_remote(self, remote_name, doc_id=None):
        '''This will push the master branch to the remote named `remote_name`
        using the mirroring strategy to cut down on locking of the working repo.

        `doc_id` is used to determine which shard should be pushed.
        if `doc_id is None, all shards are pushed.
        '''
        if doc_id is None:
            ret = True
            #@TODO should spawn a thread of each shard...
            for shard in self._shards:
                if not shard.push_to_remote(remote_name):
                    ret = False
            return ret
        shard = self.get_shard(doc_id)
        return shard.push_to_remote(remote_name)

    def commit_and_try_merge2master(self,
                                    file_content,
                                    doc_id,
                                    auth_info,
                                    parent_sha,
                                    commit_msg='',
                                    merged_sha=None):
        from peyotl.git_storage.git_workflow import generic_commit_and_try_merge2master_wf
        git_action = self.create_git_action(doc_id)
        resp = generic_commit_and_try_merge2master_wf(git_action,
                                                      file_content,
                                                      doc_id,
                                                      auth_info,
                                                      parent_sha,
                                                      commit_msg,
                                                      merged_sha=merged_sha)
        if not resp['merge_needed']:
            self._doc_merged_hook(git_action, doc_id)
        return resp
    def annotate_and_write(self, #pylint: disable=R0201
                           git_data,
                           nexson,
                           doc_id,
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
        return self.commit_and_try_merge2master(file_content=nexson,
                                                doc_id=doc_id,
                                                auth_info=auth_info,
                                                parent_sha=parent_sha,
                                                commit_msg=commit_msg,
                                                merged_sha=master_file_blob_included)
    def delete_doc(self, doc_id, auth_info, parent_sha, **kwargs):
        git_action = self.create_git_action(doc_id)
        from peyotl.phylesystem.git_workflows import delete_study
        ret = delete_study(git_action, doc_id, auth_info, parent_sha, **kwargs)   #TODO:git-workflow-edits
        if not ret['merge_needed']:
            with self._index_lock:
                try:
                    _shard = self._doc2shard_map[doc_id]
                except KeyError:
                    pass
                else:
                    alias_list = _shard.id_alias_list_fn(doc_id)
                    for alias in alias_list:
                        try:
                            del self._doc2shard_map[alias]
                        except KeyError:
                            pass
                    _shard.delete_doc_from_index(doc_id)
        return ret
    def iter_doc_objs(self, **kwargs):
        '''Generator that iterates over all detected documents (eg, nexson studies)
        and returns the doc object (deserialized from JSON) for each doc.
        Order is by shard, but arbitrary within shards.
        @TEMP not locked to prevent doc creation/deletion
        '''
        for shard in self._shards:
            for doc_id, blob in shard.iter_doc_objs(**kwargs):
                yield doc_id, blob
    def iter_doc_filepaths(self, **kwargs):
        '''Generator that iterates over all detected documents.
        and returns the filesystem path to each doc.
        Order is by shard, but arbitrary within shards.
        @TEMP not locked to prevent doc creation/deletion
        '''
        for shard in self._shards:
            for doc_id, blob in shard.iter_doc_filepaths(**kwargs):
                yield doc_id, blob
    def pull(self, remote='origin', branch_name='master'):
        with self._index_lock:
            for shard in self._shards:
                shard.pull(remote=remote, branch_name=branch_name)
            self._locked_refresh_doc_ids()
    def report_configuration(self):
        out = StringIO()
        self.write_configuration(out)
        return out.getvalue()
    def write_configuration(self, out, secret_attrs=False):
        """Generic configuration, may be overridden by type-specific version"""
        key_order = ['assumed_doc_version',
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
        """Generic configuration, may be overridden by type-specific version"""
        cd = {'assumed_doc_version': self.assumed_doc_version,
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
    def get_changed_docs(self, ancestral_commit_sha, doc_ids_to_check=None):
        ret = None
        for i in self._shards:
            x = i.get_changed_docs(ancestral_commit_sha, doc_ids_to_check=doc_ids_to_check)
            if x is not False:
                ret = x
                break
        if ret is not None:
            return ret
        raise ValueError('No docstore shard returned changed documents for the SHA')
    def get_doc_ids(self, include_aliases=False):
        k = []
        for shard in self._shards:
            k.extend(shard.get_doc_ids(include_aliases=include_aliases))
        return k

