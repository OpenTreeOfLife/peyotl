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
from peyotl.git_storage import ShardedDocStore, \
                               TypeAwareDocStore
from peyotl.phylesystem.helper import get_repos, \
                                      _get_phylesystem_parent_with_source, \
                                      _make_phylesystem_cache_region
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

class _TreeCollectionStore(TypeAwareDocStore):
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
        from peyotl.phylesystem.git_shard import PhylesystemShard   #TODO:remove-me
        TypeAwareDocStore.__init__(self,
                                   prefix_from_doc_id=prefix_from_collection_path,
                                   repos_dict=None,
                                   repos_par=None,
                                   with_caching=True,
                                   assumed_doc_version=None,
                                   git_ssh=None,
                                   pkey=None,
                                   git_action_class=GitAction,
                                   git_shard_class=PhylesystemShard,  #TODO:type-specific
                                   mirror_info=None,
                                   new_doc_prefix=None,
                                   infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                                   **kwargs)

        # rename some generic members in the base class, for clarity and backward compatibility
        @property
        def get_collection_ids(self):
            return self.get_doc_ids

_THE_TREE_COLLECTION_STORE = None
def TreeCollectionStore(repos_dict=None,
                        repos_par=None,
                        with_caching=True,
                        #repo_nexml2json=None,
                        git_ssh=None,
                        pkey=None,
                        git_action_class=GitAction,
                        mirror_info=None,
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
                                        infrastructure_commit_author=infrastructure_commit_author)
    return _THE_TREE_COLLECTION_STORE

