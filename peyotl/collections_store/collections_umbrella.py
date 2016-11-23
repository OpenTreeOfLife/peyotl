# Simplified from peyotl.phylesystem.phylesystem_umbrella
#
# A collection id should be a unique "path" string composed
#     of '{owner_id}/{slugified-collection-name}'
#     EXAMPLES: 'jimallman/trees-about-bees'
#               'jimallman/other-interesting-stuff'
#               'kcranston/trees-about-bees'
#               'jimallman/trees-about-bees-2'
#
from peyotl.utility import get_logger
from peyotl.utility.str_util import slugify, increment_slug
import json

try:
    import anyjson
except:
    class Wrapper(object):
        pass


    anyjson = Wrapper()
    anyjson.loads = json.loads
from peyotl.git_storage import ShardedDocStore, TypeAwareDocStore
from peyotl.collections_store.collections_shard import TreeCollectionsShardProxy, TreeCollectionsShard
from peyotl.collections_store.validation import validate_collection
from peyotl.collections_store.git_actions import TreeCollectionsGitAction
# from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
#                                             delete_study, \
#                                             validate_and_convert_nexson
# from peyotl.nexson_validation import ot_validate
import re

OWNER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+$')
COLLECTION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+/[a-z0-9-]+$')
# Allow simple slug-ified strings and slash separator (no whitespace!)

_LOG = get_logger(__name__)


def prefix_from_collection_path(collection_id):
    # The collection id is a sort of "path", e.g. '{owner_id}/{collection-name-as-slug}'
    #   EXAMPLES: 'jimallman/trees-about-bees', 'kcranston/interesting-trees-2'
    # Assume that the owner_id will work as a prefix, esp. by assigning all of a
    # user's collections to a single shard.for grouping in shards
    _LOG.debug('> prefix_from_collection_path(), testing this id: {i}'.format(i=collection_id))
    path_parts = collection_id.split('/')
    _LOG.debug('> prefix_from_collection_path(), found {} path parts'.format(len(path_parts)))
    if len(path_parts) > 1:
        owner_id = path_parts[0]
    elif path_parts[0] == '':
        owner_id = 'anonymous'
    else:
        owner_id = 'anonymous'  # or perhaps None?
    return owner_id


class TreeCollectionStoreProxy(ShardedDocStore):
    """Proxy for interacting with external resources if given the configuration of a remote TreeCollectionStore
    """

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
    """Wrapper around a set of sharded git repos.
    """

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
        """
        Repos can be found by passing in a `repos_par` (a directory that is the parent of the repos)
            or by trusting the `repos_dict` mapping of name to repo filepath.
        `with_caching` should be True for non-debugging uses.
        `assumed_doc_version` is optional. If specified all TreeCollectionsShard repos are assumed to store
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
        """
        TypeAwareDocStore.__init__(self,
                                   prefix_from_doc_id=prefix_from_collection_path,
                                   repos_dict=repos_dict,
                                   repos_par=repos_par,
                                   with_caching=with_caching,
                                   assumed_doc_version=assumed_doc_version,
                                   git_ssh=git_ssh,
                                   pkey=pkey,
                                   git_action_class=TreeCollectionsGitAction,
                                   git_shard_class=TreeCollectionsShard,
                                   mirror_info=mirror_info,
                                   new_doc_prefix=None,
                                   infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                                   **kwargs)

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def get_collection_ids(self):
        return self.get_doc_ids

    @property
    def delete_collection(self):
        return self.delete_doc

    def create_git_action_for_new_collection(self, new_collection_id=None):
        """Checks out master branch of the shard as a side effect"""
        return self._growing_shard.create_git_action_for_new_collection(new_collection_id=new_collection_id)

    def add_new_collection(self,
                           owner_id,
                           json_repr,
                           auth_info,
                           collection_id=None,
                           commit_msg=''):
        """Validate and save this JSON. Ensure (and return) a unique collection id"""
        collection = self._coerce_json_to_collection(json_repr)
        if collection is None:
            msg = "File failed to parse as JSON:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not self._is_valid_collection_json(collection):
            msg = "JSON is not a valid collection:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if collection_id:
            # try to use this id
            found_owner_id, slug = collection_id.split('/')
            assert found_owner_id == owner_id
        else:
            # extract a working title and "slugify" it
            slug = self._slugify_internal_collection_name(json_repr)
            collection_id = '{i}/{s}'.format(i=owner_id, s=slug)
        # Check the proposed id for uniqueness in any case. Increment until
        # we have a new id, then "reserve" it using a placeholder value.
        with self._index_lock:
            while collection_id in self._doc2shard_map:
                collection_id = increment_slug(collection_id)
            self._doc2shard_map[collection_id] = None
        # pass the id and collection JSON to a proper git action
        new_collection_id = None
        r = None
        try:
            # assign the new id to a shard (important prep for commit_and_try_merge2master)
            gd_id_pair = self.create_git_action_for_new_collection(new_collection_id=collection_id)
            new_collection_id = gd_id_pair[1]
            try:
                # let's remove the 'url' field; it will be restored when the doc is fetched (via API)
                del collection['url']
                # keep it simple (collection is already validated! no annotations needed!)
                r = self.commit_and_try_merge2master(file_content=collection,
                                                     doc_id=new_collection_id,
                                                     auth_info=auth_info,
                                                     parent_sha=None,
                                                     commit_msg=commit_msg,
                                                     merged_sha=None)
            except:
                self._growing_shard.delete_doc_from_index(new_collection_id)
                raise
        except:
            with self._index_lock:
                if new_collection_id in self._doc2shard_map:
                    del self._doc2shard_map[new_collection_id]
            raise
        with self._index_lock:
            self._doc2shard_map[new_collection_id] = self._growing_shard
        return new_collection_id, r

    def update_existing_collection(self,
                                   owner_id,
                                   collection_id=None,
                                   json_repr=None,
                                   auth_info=None,
                                   parent_sha=None,
                                   merged_sha=None,
                                   commit_msg=''):
        """Validate and save this JSON. Ensure (and return) a unique collection id"""
        collection = self._coerce_json_to_collection(json_repr)
        if collection is None:
            msg = "File failed to parse as JSON:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not self._is_valid_collection_json(collection):
            msg = "JSON is not a valid collection:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not collection_id:
            raise ValueError("Collection id not provided (or invalid)")
        if not self.has_doc(collection_id):
            msg = "Unexpected collection id '{}' (expected an existing id!)".format(collection_id)
            raise ValueError(msg)
        # pass the id and collection JSON to a proper git action
        r = None
        try:
            # remove any 'url' field before saving; it will be restored when the doc is fetched (via API)
            if 'url' in collection:
                del collection['url']
            # keep it simple (collection is already validated! no annotations needed!)
            r = self.commit_and_try_merge2master(file_content=collection,
                                                 doc_id=collection_id,
                                                 auth_info=auth_info,
                                                 parent_sha=parent_sha,
                                                 commit_msg=commit_msg,
                                                 merged_sha=merged_sha)
            # identify shard for this id!?
        except:
            raise
        return r

    def copy_existing_collection(self, owner_id, old_collection_id):
        """Ensure a unique id, whether from the same user or a different one"""
        raise NotImplementedError('TODO')

    def rename_existing_collection(self, owner_id, old_collection_id, new_slug=None):
        """Use slug provided, or use internal name to generate a new id"""
        raise NotImplementedError('TODO')

    def _slugify_internal_collection_name(self, json_repr):
        """Parse the JSON, find its name, return a slug of its name"""
        collection = self._coerce_json_to_collection(json_repr)
        if collection is None:
            return None
        internal_name = collection['name']
        return slugify(internal_name)

    def _is_valid_collection_id(self, test_id):
        """Test for the expected format '{owner_id}/{slug}', return T/F
        N.B. This does not test for a working GitHub username!"""
        return bool(COLLECTION_ID_PATTERN.match(test_id))

    def _is_existing_id(self, test_id):
        """Test to see if this id is non-unique (already exists in a shard)"""
        return test_id in self.get_collection_ids()

    def _is_valid_collection_json(self, json_repr):
        """Call the primary validator for a quick test"""
        collection = self._coerce_json_to_collection(json_repr)
        if collection is None:
            # invalid JSON, definitely broken
            return False
        aa = validate_collection(collection)
        errors = aa[0]
        for e in errors:
            _LOG.debug('> invalid JSON: {m}'.format(m=e.encode('utf-8')))
        if len(errors) > 0:
            return False
        return True

    def _coerce_json_to_collection(self, json_repr):
        """Use to ensure that a JSON string (if found) is parsed to the equivalent dict in python.
        If the incoming value is already parsed, do nothing. If a string fails to parse, return None."""
        if isinstance(json_repr, dict):
            collection = json_repr
        else:
            try:
                collection = anyjson.loads(json_repr)
            except:
                _LOG.warn('> invalid JSON (failed anyjson parsing)')
                return None
        return collection


_THE_TREE_COLLECTION_STORE = None


# noinspection PyPep8Naming
def TreeCollectionStore(repos_dict=None,
                        repos_par=None,
                        with_caching=True,
                        assumed_doc_version=None,
                        git_ssh=None,
                        pkey=None,
                        git_action_class=TreeCollectionsGitAction,
                        mirror_info=None,
                        infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>'):
    """Factory function for a _TreeCollectionStore object.

    A wrapper around the _TreeCollectionStore class instantiation for
    the most common use case: a singleton _TreeCollectionStore.
    If you need distinct _TreeCollectionStore objects, you'll need to
    call that class directly.
    """
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
