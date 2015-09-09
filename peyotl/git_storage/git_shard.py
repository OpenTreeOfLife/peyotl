"""Base class for individual shard (repo) used in a doc store.
   Subclasses will accommodate each type."""
import os
import codecs
import anyjson
from threading import Lock
from peyotl.utility import get_logger, \
                           write_to_filepath
from peyotl.utility.input_output import read_as_json, write_as_json

class FailedShardCreationError(ValueError):
    def __init__(self, message):
        ValueError.__init__(self, message)

class GitShard(object):
    """Bare-bones functionality needed by both normal and proxy shards."""
    def __init__(self, name):
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
    @doc_index.setter
    def doc_index(self, val):
        self._doc_index = val

    def get_doc_ids(self, **kwargs):
        with self._index_lock:
            k = self._doc_index.keys()
        return list(k)

class TypeAwareGitShard(GitShard):
    """Adds hooks for type-specific behavior in subclasses.
    """
    def __init__(self,
                 name,
                 path,
                 doc_holder_subpath='',
                 assumed_doc_version=None,
                 detect_doc_version_fn=None,
                 refresh_doc_index_fn=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=None,
                 push_mirror_repo_path=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        GitShard.__init__(self, name)
        self.filepath_for_doc_id_fn = None # overwritten in refresh_doc_index_fn
        self.id_alias_list_fn = None  # overwritten in refresh_doc_index_fn
        self._infrastructure_commit_author = infrastructure_commit_author
        self._locked_refresh_doc_index = refresh_doc_index_fn
        self._master_branch_repo_lock = Lock()
        self._ga_class = git_action_class
        self.git_ssh = git_ssh
        self.pkey = pkey
        path = os.path.abspath(path)
        dot_git = os.path.join(path, '.git')
        doc_dir = os.path.join(path, doc_holder_subpath)  # type-specific, e.g. 'study'
        if not os.path.isdir(path):
            raise FailedShardCreationError('"{p}" is not a directory'.format(p=path))
        if not os.path.isdir(dot_git):
            raise FailedShardCreationError('"{p}" is not a directory'.format(p=dot_git))
        if not os.path.isdir(doc_dir):
            raise FailedShardCreationError('"{p}" is not a directory'.format(p=doc_dir))
        self.path = path
        self.doc_dir = doc_dir
        with self._index_lock:
            self._locked_refresh_doc_index(self, initializing=True)
        self.parent_path = os.path.split(path)[0] + '/'
        self.git_dir = dot_git
        self.push_mirror_repo_path = push_mirror_repo_path
        if assumed_doc_version is None:
            _LOG = get_logger('TypeAwareGitShard')
            try:
                # pass this shard to a type-specific test
                assumed_doc_version = detect_doc_version_fn(self)
            except IndexError as x:
                # no documents in this shard!
                _LOG.warn('No documents in this shard! Auto-detection of assumed_doc_version failed.')
            except Exception as x:
                f = 'Auto-detection of assumed_doc_version FAILED with this error:\n{}'
                f = f.format(str(x))
                _LOG.warn(f)
            except:
                pass
        max_file_size = kwargs.get('max_file_size')
        if max_file_size is None:
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

    def delete_doc_from_index(self, doc_id):
        try:
            # some types use aliases, e.g. '123', 'pg_123'
            alias_list = self.id_alias_list_fn(doc_id)  #pylint: disable=E1102
        except AttributeError:
            # simpler types don't use aliases
            alias_list = [doc_id]
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
                              path_for_doc_fn=self.filepath_for_doc_id_fn,
                              max_file_size=self.max_file_size)
    def pull(self, remote='origin', branch_name='master'):
        with self._index_lock:
            ga = self.create_git_action()
            from peyotl.git_storage.git_workflow import _pull_gh
            _pull_gh(ga, remote, branch_name)
            self._locked_refresh_doc_index(self)
    def register_doc_id(self, ga, doc_id):
        fp = ga.path_for_doc(doc_id)
        with self._index_lock:
            self._doc_index[doc_id] = (self.name, self.doc_dir, fp)
    def _create_git_action_for_mirror(self):
        # If a document makes it into the working dir, we don't want to reject it from the mirror, so
        #   we use max_file_size= None
        mirror_ga = self._ga_class(repo=self.push_mirror_repo_path,
                                   git_ssh=self.git_ssh,
                                   pkey=self.pkey,
                                   path_for_doc_fn=self.filepath_for_doc_id_fn,
                                   max_file_size=None)
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
        try:
            # some types use aliases, e.g. '123', 'pg_123'
            alias_list = self.id_alias_list_fn(doc_id)  #pylint: disable=E1102
        except AttributeError:
            # simpler types don't use aliases
            return False
        # some types use aliases, e.g. '123', 'pg_123'
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
                        yield (doc_id, nex_obj)
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
            si = self._doc_index
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
        return ga.get_changed_docs(ancestral_commit_sha, doc_ids_to_check=doc_ids_to_check)
        #TODO:git-action-edits

    def _create_git_action_for_global_resource(self):
        """This should be implemented by all subclasses"""
        raise NotImplementedError('Type-specific shard class should have "_create_git_action_for_global_resource" method')
    def _read_master_branch_resource(self, fn, is_json=False):
        '''This will force the current branch to master! '''
        with self._master_branch_repo_lock:
            ga = self._create_git_action_for_global_resource()
            with ga.lock():
                ga.checkout_master()
                if os.path.exists(fn):
                    if is_json:
                        return read_as_json(fn)
                    with codecs.open(fn, 'rU', encoding='utf-8') as f:
                        ret = f.read()
                    return ret
                return None
    def _write_master_branch_resource(self, content, fn, commit_msg, is_json=False):
        '''This will force the current branch to master! '''
        #TODO: we might want this to push, but currently it is only called in contexts in which
        # we are about to push anyway (document creation)
        with self._master_branch_repo_lock:
            ga = self._create_git_action_for_global_resource()
            with ga.lock():
                ga.checkout_master()
                if is_json:
                    write_as_json(content, fn)
                else:
                    write_to_filepath(content, fn)
                ga._add_and_commit(fn, self._infrastructure_commit_author, commit_msg)

def _invert_dict_list_val(d):
    o = {}
    for k, v in d.items():
        o.setdefault(v, []).append(k)
    for v in o.values():
        v.sort()
    return o
