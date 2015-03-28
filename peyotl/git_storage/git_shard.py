"""Base class for individual shard (repo) used in a doc store.
   Subclasses will accommodate each type."""
import os
import re
import codecs
from threading import Lock
from peyotl.utility import get_logger, get_config_setting_kwargs, write_to_filepath
from peyotl.utility.input_output import read_as_json, write_as_json

class NotAGitShardError(ValueError):
    def __init__(self, message):
        ValueError.__init__(self, message)

class GitShard(object):
    """Bare-bones functionality needed by both normal and proxy shards."""
    def __init__(self, name):
        from peyotl.phylesystem.helper import DIGIT_PATTERN, create_id2study_info, diagnose_repo_study_id_convention
        self._index_lock = Lock()
        self._doc_index = {}
        self.name = name
        self.path = ' '
        # ' ' mimics place of the abspath of repo in path -> relpath mapping
        self.has_aliases = False
    #pylint: disable=E1101
    def get_rel_path_fragment(self, doc_id):
        '''For `doc_id` returns the path from the
        repo to the doc file. This is useful because
        (if you know the remote), it lets you construct the full path.
        '''
        with self._index_lock:
            r = self._doc_index[doc_id]
        fp = r[-1]
        return fp[(len(self.path) + 1):] # "+ 1" to remove the /
    @property
    def doc_index(self):
        return self._doc_index

    #TODO:type-specific
    def get_doc_ids(self, include_aliases=False):
        with self._index_lock:
            k = self._doc_index.keys()
        if self.has_aliases and (not include_aliases):
            x = []
            for i in k:
                if DIGIT_PATTERN.match(i) or ((len(i) > 1) and (i[-2] == '_')):
                    pass
                else:
                    x.append(i)
            return x
        return list(k)

class TypeAwareGitShard(GitShard):
    """Adds hooks for type-specific behavior in subclasses.
    """
    def __init__(self,
                 name,
                 path,
                 assumed_doc_version=None,
                 detect_doc_version_fn=None,
                 refresh_doc_index_fn=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=None,  #TODO:peyotl.phylesystem.git_actions.GitAction,
                 push_mirror_repo_path=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        GitShard.__init__(self, name)
        self._infrastructure_commit_author = infrastructure_commit_author
        self._locked_refresh_doc_ids = refresh_doc_index_fn
        self._master_branch_repo_lock = Lock()
        self._ga_class = git_action_class
        self.git_ssh = git_ssh
        self.pkey = pkey
        path = os.path.abspath(path)
        dot_git = os.path.join(path, '.git')
        doc_dir = os.path.join(path, 'study')  #TODO:type-specific
        if not os.path.isdir(path):
            raise NotAPhylesystemShardError('"{p}" is not a directory'.format(p=path))
        if not os.path.isdir(dot_git):
            raise NotAPhylesystemShardError('"{p}" is not a directory'.format(p=dot_git))
        if not os.path.isdir(doc_dir):
            raise NotAPhylesystemShardError('"{p}" is not a directory'.format(p=doc_dir))
        self.path = path
        from peyotl.phylesystem.helper import create_id2study_info, \
                                              diagnose_repo_study_id_convention
        d = create_id2study_info(doc_dir, name)
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
            self.inferred_study_prefix = True
            self.infer_study_prefix()
        else:
            self.inferred_study_prefix = False
        self.doc_dir = doc_dir
        with self._index_lock:
            self._locked_refresh_doc_ids(self)
        self.parent_path = os.path.split(path)[0] + '/'
        self.git_dir = dot_git
        self.push_mirror_repo_path = push_mirror_repo_path
        if assumed_doc_version is None:
            try:
                assumed_doc_version = get_config_setting_kwargs(None, 'phylesystem', 'repo_nexml2json', **kwargs)
            except:
                pass
            if assumed_doc_version == None:
                try:
                    # pass this shard to a type-specific test
                    assumed_doc_version = detect_doc_version_fn(self)
                except:
                    pass
        max_file_size = kwargs.get('max_file_size')
        if max_file_size is None:
            max_file_size = get_config_setting_kwargs(None, 'phylesystem', 'max_file_size', default=None, **kwargs)
            if max_file_size is not None:
                try:
                    max_file_size = int(max_file_size)
                except:
                    m = 'Configuration-base value of max_file_size was "{}". Expecting an integer.'
                    m = m.format(max_file_size)
                    raise RuntimeError(m)
        self.max_file_size = max_file_size
        self.assumed_doc_version = assumed_doc_version
        self._known_prefixes = None
        pass

    def delete_doc_from_index(self, doc_id):
        alias_list = self.id_alias_list_fn(doc_id)
        with self._index_lock:
            for i in alias_list:
                try:
                    del self._doc_index[i]
                except:
                    pass
    def create_git_action(self):
        return self._ga_class(repo=self.path,
                              git_ssh=self.git_ssh,
                              pkey=self.pkey,
                              path_for_study_fn=self.filepath_for_study_id_fn,
                              max_file_size=self.max_file_size)
        #TODO:git-action-edits
    def pull(self, remote='origin', branch_name='master'):
        with self._index_lock:
            ga = self.create_git_action()
            from peyotl.phylesystem.git_workflows import _pull_gh
            _pull_gh(ga, remote, branch_name)
            self._locked_refresh_doc_ids(self)
    #TODO:type-specific?
    def register_study_id(self, ga, study_id):
        fp = ga.path_for_study(study_id)
        with self._index_lock:
            self._study_index[study_id] = (self.name, self.doc_dir, fp)
    def _create_git_action_for_mirror(self):
        # If a document makes it into the working dir, we don't want to reject it from the mirror, so
        #   we use max_file_size= None
        mirror_ga = self._ga_class(repo=self.push_mirror_repo_path,
                                   git_ssh=self.git_ssh,
                                   pkey=self.pkey,
                                   path_for_study_fn=self.filepath_for_study_id_fn,
                                   max_file_size=None)
        #TODO:git-action-edits
        return mirror_ga
    def push_to_remote(self, remote_name):
        if self.push_mirror_repo_path is None:
            raise RuntimeError('This {} has no push mirror, so it cannot push to a remote.'.format(type(self)))
        working_ga = self.create_git_action()
        mirror_ga = self._create_git_action_for_mirror()
        with mirror_ga.lock():
            with working_ga.lock():
                mirror_ga.fetch(remote='origin')
            mirror_ga.merge('origin/master', destination='master')
            mirror_ga.push(branch='master',
                           remote=remote_name)
        return True
    def _is_alias(self, doc_id):
        alias_list = self.id_alias_list_fn(doc_id)
        if len(alias_list) > 1:
            ml = max([len(i) for i in alias_list])
            if ml > len(doc_id):
                return True
        return False
    def iter_doc_filepaths(self, **kwargs): #pylint: disable=W0613
        '''Returns a pair: (doc_id, absolute filepath of document file)
        for each document in this repository.
        Order is arbitrary.
        '''
        with self._index_lock:
            for doc_id, info in self._doc_index.items():
                if not self._is_alias(doc_id):
                    yield doc_id, info[-1]

    #TODO:type-specific? Where and how is this used?
    def iter_doc_objs(self, **kwargs):
        '''Returns a pair: (doc_id, nexson_blob)
        for each document in this repository.
        Order is arbitrary.
        '''
        for doc_id, fp in self.iter_doc_filepaths(**kwargs):
            if not self._is_alias(doc_id):
                #TODO:hook for type-specific parser?
                with codecs.open(fp, 'r', 'utf-8') as fo:
                    try:
                        nex_obj = anyjson.loads(fo.read())
                        yield (obj_id, nex_obj)
                    except Exception:
                        pass

    def write_configuration(self, out, secret_attrs=False):
        """Generic configuration, may be overridden by type-specific version"""
        key_order = ['name', 'path', 'git_dir', 'doc_dir', 'assumed_doc_version',
                     'git_ssh', 'pkey', 'has_aliases', 'number of documents']
        cd = self.get_configuration_dict(secret_attrs=secret_attrs)
        for k in key_order:
            if k in cd:
                out.write('  {} = {}'.format(k, cd[k]))
        out.write('  documents in alias groups:\n')
        for o in cd['documents']:
            out.write('    {} ==> {}\n'.format(o['keys'], o['relpath']))
    def get_configuration_dict(self, secret_attrs=False):
        """Generic configuration, may be overridden by type-specific version"""
        rd = {'name': self.name,
              'path': self.path,
              'git_dir': self.git_dir,
              'assumed_doc_version': self.assumed_doc_version,
              'doc_dir': self.doc_dir,
              'git_ssh': self.git_ssh, }
        if secret_attrs:
            rd['pkey'] = self.pkey
        with self._index_lock:
            si = self._study_index
        r = _invert_dict_list_val(si)
        key_list = list(r.keys())
        rd['number of documents'] = len(key_list)
        key_list.sort()
        m = []
        for k in key_list:
            v = r[k]
            fp = k[2]
            assert fp.startswith(self.doc_dir)
            rp = fp[len(self.doc_dir) + 1:]
            m.append({'keys': v, 'relpath': rp})
        rd['documents'] = m
        return rd

    def get_branch_list(self):
        ga = self.create_git_action()
        return ga.get_branch_list()
    def get_changed_docs(self, ancestral_commit_sha, doc_ids_to_check=None):
        ga = self.create_git_action()
        return ga.get_changed_studies(ancestral_commit_sha, study_ids_to_check=doc_ids_to_check)
        #TODO:git-action-edits

def _invert_dict_list_val(d):
    o = {}
    for k, v in d.items():
        o.setdefault(v, []).append(k)
    for v in o.values():
        v.sort()
    return o
