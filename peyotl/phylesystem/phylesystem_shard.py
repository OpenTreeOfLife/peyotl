import json
import codecs
from peyotl.utility import get_logger
from peyotl.git_storage.git_shard import GitShard, \
                                         TypeAwareGitShard
from peyotl.phylesystem.git_actions import GitAction

_LOG = get_logger(__name__)
#class PhylesystemShardBase(object):

class PhylesystemShardProxy(GitShard):
    '''Proxy for shard when interacting with external resources if given the configuration of a remote Phylesystem
    '''
    def __init__(self, config):
        GitShard.__init__(self, config['name'])
        self.repo_nexml2json = config['repo_nexml2json']
        d = {}
        for study in config['studies']:
            kl = study['keys']
            if len(kl) > 1:
                self.has_aliases = True
            for k in study['keys']:
                d[k] = (self.name, self.path, self.path + '/study/' + study['relpath'])
        self.study_index = d

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def get_study_ids(self):
        return self.get_doc_ids
    @property
    def return_study(self):
        return self.return_doc
    @property
    def get_changed_studies(self):
        return self.get_changed_docs
    @property
    def _mint_new_study_id(self):
        return self._mint_new_doc_id

    @property
    def repo_nexml2json(self):
        return self.assumed_doc_version
    @repo_nexml2json.setter
    def repo_nexml2json(self,val):
        self.assumed_doc_version = val

    @property
    def study_index(self):
        return self.doc_index
    @study_index.setter
    def study_index(self,val):
        self._doc_index = val

    @property
    def new_study_prefix(self):
        return self.new_doc_prefix
    @new_study_prefix.setter
    def new_study_prefix(self,val):
        self.new_doc_prefix = val

class NotAPhylesystemShardError(ValueError):
    def __init__(self, message):
        ValueError.__init__(self, message)

def diagnose_repo_nexml2json(shard):
    """Optimistic test for Nexson version in a shard (tests first study found)"""
    with shard._index_lock:
        fp = shard.study_index.values()[0][2]
    _LOG.debug('diagnose_repo_nexml2json with fp={}'.format(fp))
    with codecs.open(fp, mode='r', encoding='utf-8') as fo:
        fj = json.load(fo)
        from peyotl.nexson_syntax import detect_nexson_version
        return detect_nexson_version(fj)

def refresh_study_index(shard):
    from peyotl.phylesystem.helper import create_id2study_info, \
                                          diagnose_repo_study_id_convention
    d = create_id2study_info(shard.study_dir, shard.name)
    rc_dict = diagnose_repo_study_id_convention(shard.path)
    shard.filepath_for_study_id_fn = rc_dict['fp_fn']
    shard.id_alias_list_fn = rc_dict['id2alias_list']
    if rc_dict['convention'] != 'simple':
        a = {}
        for k, v in d.items():
            alias_list = shard.id_alias_list_fn(k)
            for alias in alias_list:
                a[alias] = v
        d = a
        shard.has_aliases = True
    else:
        shard.has_aliases = False
    shard._study_index = d

class PhylesystemShard(TypeAwareGitShard):
    '''Wrapper around a git repo holding nexson studies.
    Raises a ValueError if the directory does not appear to be a PhylesystemShard.
    Raises a RuntimeError for errors associated with misconfiguration.'''
    def __init__(self,
                 name,
                 path,
                 repo_nexml2json=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=GitAction,
                 push_mirror_repo_path=None,
                 new_study_prefix=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        TypeAwareGitShard.__init__(self, 
                                   name,
                                   path,
                                   repo_nexml2json,
                                   diagnose_repo_nexml2json,  # version detection
                                   refresh_study_index,  # populates 'study_index'
                                   git_ssh,
                                   pkey,
                                   git_action_class,
                                   push_mirror_repo_path,
                                   new_study_prefix,   #TODO
                                   infrastructure_commit_author,
                                   **kwargs)

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def get_study_ids(self):
        return self.get_doc_ids
    @property
    def iter_study_objs(self):
        return self.iter_doc_objs
    @property
    def iter_study_filepaths(self):
        return self.iter_doc_filepaths
    @property
    def get_changed_studies(self):
        return self.get_changed_docs
    @property
    def known_prefixes(self):
        if self._known_prefixes is None:
            self._known_prefixes = self._diagnose_prefixes()
        return self._known_prefixes
    @property
    def new_study_prefix(self):
        return self._new_study_prefix

    @property
    def study_index(self):
        return self.doc_index
    @study_index.setter
    def study_index(self,val):
        self._doc_index = val

    @property
    def repo_nexml2json(self):
        return self.assumed_doc_version
    @repo_nexml2json.setter
    def repo_nexml2json(self,val):
        self.assumed_doc_version = val

