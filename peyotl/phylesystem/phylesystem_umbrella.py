from peyotl.utility import get_logger
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import json
try:
    from dogpile.cache.api import NO_VALUE
except:
    pass #caching is optional
from peyotl.phylesystem.helper import get_repos, \
                                      _get_phylesystem_parent_with_source, \
                                      _make_phylesystem_cache_region
from peyotl.git_storage import ShardedDocStore, \
                               TypeAwareDocStore
from peyotl.phylesystem.phylesystem_shard import PhylesystemShardProxy, \
                                                 PhylesystemShard, \
                                                 NotAPhylesystemShardError
from peyotl.phylesystem.git_actions import GitAction
from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
                                             delete_study, \
                                             validate_and_convert_nexson
from peyotl.nexson_validation import ot_validate
from peyotl.nexson_validation._validation_base import NexsonAnnotationAdder, \
                                                      replace_same_agent_annotation
import os
import re
STUDY_ID_PATTERN = re.compile(r'[a-zA-Z][a-zA-Z]_[0-9]+')
_LOG = get_logger(__name__)

def prefix_from_study_id(study_id):
    # TODO: Use something smarter here, splitting on underscore?
    return study_id[:3]

class PhylesystemProxy(ShardedDocStore):
    '''Proxy for interacting with external resources if given the configuration of a remote Phylesystem.
    N.B. that this has minimal functionality, and is mainly used to fetch studies and their ids.
    '''
    def __init__(self, config):
        ShardedDocStore.__init__(self,
                                 prefix_from_doc_id=prefix_from_study_id)
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
        self._doc2shard_map = d

class _Phylesystem(TypeAwareDocStore):
    '''Wrapper around a set of sharded git repos, with business rules specific to Nexson studies.
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
        TypeAwareDocStore.__init__(self,
                                   prefix_from_doc_id=prefix_from_study_id,
                                   repos_dict=None,
                                   repos_par=None,
                                   with_caching=True,
                                   assumed_doc_version=repo_nexml2json,
                                   git_ssh=None,
                                   pkey=None,
                                   git_action_class=GitAction,
                                   git_shard_class=PhylesystemShard,
                                   mirror_info=None,
                                   new_doc_prefix=None,
                                   infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                                   **kwargs)

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
    def new_study_prefix(self):
        return self.new_doc_prefix
    @new_study_prefix.setter
    def new_study_prefix(self,val):
        self.new_doc_prefix = val

    @property
    def repo_nexml2json(self):
        return self.assumed_doc_version
    @repo_nexml2json.setter
    def repo_nexml2json(self,val):
        self.assumed_doc_version = val

        ##  # rename some generic methods in the base class, for clarity and backward compatibility
        ##  self.get_study_ids = self.get_doc_ids
        ##  self.return_study = self.return_doc
        ##  self.get_changed_studies = self.get_changed_docs
        ##  self._mint_new_study_id = self._mint_new_doc_id
        ## 
        ##  # rename some generic attributes in the base class, for clarity and backward compatibility
        ##  renamed_attributes = {'new_study_prefix':   'new_doc_prefix',
        ##                        'repo_nexml2json':    'assumed_doc_version',
        ##                        '_study2shard_map':   '_doc2shard_map'}
        ##  def __getattr__(self, name):
        ##      if type_specific_name in renamed_attributes.key():
        ##          generic_attr_name = renamed_attributes[type_specific_name]
        ##          return TypeAwareDocStore.__getattr(self, generic_attr_name)
        ##      else:
        ##          return TypeAwareDocStore.__getattr(self, name)
        ##  def __setattr__(self, name, value):
        ##      if type_specific_name in renamed_attributes.key():
        ##          generic_attr_name = renamed_attributes[type_specific_name]
        ##          return TypeAwareDocStore.__setattr(self, generic_attr_name, value)
        ##      else:
        ##          return TypeAwareDocStore.__setattr(self, name, value)
        ##  def __delattr__(self, name):
        ##      if type_specific_name in renamed_attributes.key():
        ##          generic_attr_name = renamed_attributes[type_specific_name]
        ##          return TypeAwareDocStore.__delattr(self, generic_attr_name)
        ##      else:
        ##          return TypeAwareDocStore.__delattr(self, name)
        ##
        ##  # rename some generic methods in the base class, for clarity and backward compatibility
        ##  self.get_study_ids = self.get_doc_ids
        ##  self.return_study = self.return_doc

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

