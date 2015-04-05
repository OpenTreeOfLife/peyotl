# Simplified from peyotl.phylesystem.phylesystem_umbrella
# TODO:
#   - clobber all references to study prefix (eg, 'pg')
#   - add uniqueness test for collection_id instead
#   - a collection id should be a unique "path" string composed 
#     of '{ownerid}/{slugified-collection-name}'
#     EXAMPLES: 'jimallman/trees-about-bees'
#               'jimallman/other-interesting-stuff'
#               'kcranston/trees-about-bees'
#               'jimallman/trees-about-bees-2'
#   - refactor shard to base class, with generalized 'items'?
from peyotl.utility import get_logger
from peyotl.utility.str_util import slugify
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
from peyotl.collections.collections_shard import TreeCollectionsShardProxy, \
                                                 TreeCollectionsShard
from peyotl.collections import get_empty_collection
from peyotl.collection_validation import validate_collection
from peyotl.collections.git_actions import TreeCollectionsGitAction
#from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
#                                             delete_study, \
#                                             validate_and_convert_nexson
#from peyotl.nexson_validation import ot_validate
from threading import Lock
import os
import re

COLLECTION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+/[a-z0-9-]+$')
# Allow simple slug-ified strings and slash separator (no whitespace!)

_LOG = get_logger(__name__)

def prefix_from_collection_path(collection_id):
    # The collection id is a sort of "path", e.g. '{ownerid}/{collection-name-as-slug}'
    #   EXAMPLES: 'jimallman/trees-about-bees', 'kcranston/interesting-trees-2'
    # Assume that the ownerid will work as a prefix, esp. by assigning all of a
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
            self._shards.append(TreeCollectionsShardProxy(s))
        d = {}
        for s in self._shards:
            for k in s.doc_index.keys():
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
                 assumed_doc_version=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=TreeCollectionsGitAction,
                 mirror_info=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        '''
        Repos can be found by passing in a `repos_par` (a directory that is the parent of the repos)
            or by trusting the `repos_dict` mapping of name to repo filepath.
        `with_caching` should be True for non-debugging uses.
        `assumed_doc_version` is optional. If specified all TreeCollectionStoreShard repos are assumed to store
            files of this version of nexson syntax.
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
        TypeAwareDocStore.__init__(self,
                                   prefix_from_doc_id=prefix_from_collection_path,
                                   repos_dict=repos_dict,
                                   repos_par=None,
                                   with_caching=True,
                                   assumed_doc_version=None,
                                   git_ssh=None,
                                   pkey=None,
                                   git_action_class=TreeCollectionsGitAction,
                                   git_shard_class=TreeCollectionsShard,
                                   mirror_info=None,
                                   new_doc_prefix=None,
                                   infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                                   **kwargs)

        # rename some generic members in the base class, for clarity and backward compatibility
        @property
        def get_collection_ids(self):
            return self.get_doc_ids

        def add_new_collection(self, ownerid, json):
            """Validate and save this JSON. Ensure (and return) a unique collection id"""
            collection = self._coerce_json_to_collection(json)
            if collection is None:
                #TODO: return an exception?
                msg = "File failed to parse as JSON:\n{j}".format(j=json)
                return msg
            if not _is_valid_collection_json(self, collection):
                #TODO: return an exception?
                msg = "JSON is not a valid collection:\n{j}".format(j=json)
                return msg
            # extract a working title and make it unique
            coll_name = _slugify_internal_collection_name(json)
            kkkkk


            #TODO: pass the name and collection JSON to a proper git action

            pass

        def copy_existing_collection(self, ownerid, old_collection_id):
            """Ensure a unique id, whether from the same user or a different one"""
            pass
        
        def rename_existing_collection(self, ownerid, old_collection_id, new_slug=None):
            """Use slug provided, or use internal name to generate a new id"""
            pass

        def delete_collection(self, collection_id):
            """Find and remove the matching collection (if any)"""
            pass

        def _slugify_internal_collection_name(self, json):
            """Parse the JSON, find its name, return a slug of its name"""
            collection = self._coerce_json_to_collection(json)
            if collection is None:
                return None
            internal_name = collection['name']
            return slugify(internal_name)

        def _is_valid_collection_id(self, test_id):
            """Test for the expected format '{ownerid}/{slug}', return T/F
            N.B. This does not test for a working GitHub username!"""
            return bool(COLLECTION_ID_PATTERN.match(test_id))

        def _is_existing_id(self, test_id):
            """Test to see if this id is non-unique (already exists in a shard)"""
            pass
        
        def _is_valid_collection_json(self, json):
            """Call the primary validator for a quick test"""
            collection = self._coerce_json_to_collection(json)
            if collection is None:
                # invalid JSON, definitely broken
                return False
            aa = validate_collection(collection)
            errors = aa[0]
            for e in errors:
                _LOG.debug('> invalid JSON: {m}'.format(m=UNICODE(e)))
            if len(errors) > 0:
                return False
            return True

        def _coerce_json_to_collection(self, json):
            """Use to ensure that a JSON string (if found) is parsed to the equivalent dict in python.
            If the incoming value is already parsed, do nothing. If a string fails to parse, return None."""
            if type(json) is dict:
                collection = json
            else:
                try:
                    collection = anyjson.loads(json)
                except:
                    #TODO: raise an exception? return an error?
                    msg = "File failed to validate cleanly. See {o}".format(o=ofn)
                    return None
            return collection

_THE_TREE_COLLECTION_STORE = None
def TreeCollectionStore(repos_dict=None,
                        repos_par=None,
                        with_caching=True,
                        assumed_doc_version=None,
                        git_ssh=None,
                        pkey=None,
                        git_action_class=TreeCollectionsGitAction,
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
                                        assumed_doc_version=assumed_doc_version,
                                        git_ssh=git_ssh,
                                        pkey=pkey,
                                        git_action_class=git_action_class,
                                        mirror_info=mirror_info,
                                        infrastructure_commit_author=infrastructure_commit_author)
    return _THE_TREE_COLLECTION_STORE

