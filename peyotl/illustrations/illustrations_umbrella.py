# An illustration id should be a unique "path" string composed
#     of '{owner_id}/{slugified-illustration-name}'
#     EXAMPLES: 'jimallman/trees-about-bees'
#               'jimallman/apis-trees-butterfly-layout'
#               'kcranston/trees-about-bees'
#               'jimallman/trees-about-bees-2'
from peyotl.utility import get_logger
from peyotl.utility.str_util import slugify, \
                                    increment_slug
import json
try:
    import anyjson
except:
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads
from peyotl.git_storage import ShardedDocStore, \
                               TypeAwareDocStore
from peyotl.illustrations.illustrations_shard import IllustrationsShardProxy, \
                                                     IllustrationsShard

from peyotl.illustrations.validation import validate_illustration
from peyotl.illustrations.git_actions import IllustrationsGitAction
#from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
#                                             delete_study, \
#                                             validate_and_convert_nexson
#from peyotl.nexson_validation import ot_validate
import re
import os
import shutil

# An illustration id should be a unique string composed of a GitHub userid, a
# slash separator, and a web slug (a web-safe alphanumeric string).
OWNER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+$')
ILLUSTRATION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]+/[a-z0-9-]+$')
# Allow simple slug-ified strings and slash separator (no whitespace!)

_LOG = get_logger(__name__)

def prefix_from_illustration_path(illustration_id):
    # The illustration id is a sort of "path", e.g. '{owner_id}/{illustration-name-as-slug}'
    #   EXAMPLES: 'jimallman/trees-about-bees', 'kcranston/interesting-trees-2'
    # Assume that the owner_id will work as a prefix, esp. by assigning all of a
    # user's illustrations to a single shard.for grouping in shards
    _LOG.debug('> prefix_from_illustration_path(), testing this id: {i}'.format(i=illustration_id))
    path_parts = illustration_id.split('/')
    if len(path_parts) > 1:
        owner_id = path_parts[0]
    elif path_parts[0] == '':
        owner_id = 'anonymous'
    else:
        owner_id = 'anonymous'  # or perhaps None?
    return owner_id

class IllustrationStoreProxy(ShardedDocStore):
    '''Proxy for interacting with external resources if given the configuration of a remote IllustrationStore
    '''
    def __init__(self, config):
        ShardedDocStore.__init__(self,
                                 prefix_from_doc_id=prefix_from_illustration_path)
        for s in config.get('shards', []):
            self._shards.append(IllustrationsShardProxy(s))
        d = {}
        for s in self._shards:
            for k in s.doc_index.keys():
                if k in d:
                    raise KeyError('Illustration "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._doc2shard_map = d

class _IllustrationStore(TypeAwareDocStore):
    '''Wrapper around a set of sharded git repos.
    '''
    def __init__(self,
                 repos_dict=None,
                 repos_par=None,
                 with_caching=True,
                 assumed_doc_version=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=IllustrationsGitAction,
                 mirror_info=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        '''
        Repos can be found by passing in a `repos_par` (a directory that is the parent of the repos)
            or by trusting the `repos_dict` mapping of name to repo filepath.
        `with_caching` should be True for non-debugging uses.
        `assumed_doc_version` is optional. If specified all IllustrationsShard repos are assumed to store
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
                                   prefix_from_doc_id=prefix_from_illustration_path,
                                   repos_dict=repos_dict,
                                   repos_par=repos_par,
                                   with_caching=with_caching,
                                   assumed_doc_version=assumed_doc_version,
                                   git_ssh=git_ssh,
                                   pkey=pkey,
                                   git_action_class=IllustrationsGitAction,
                                   git_shard_class=IllustrationsShard,
                                   mirror_info=mirror_info,
                                   new_doc_prefix=None,
                                   infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                                   **kwargs)
        # add initialization steps here

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def get_illustration_ids(self):
        return self.get_doc_ids
    @property
    def delete_illustration(self):
        return self.delete_doc
    def delete_illustration_subresource(self, *args, **kwargs):
        if not kwargs.get('subresource_path', None):
            raise ValueError("Sub-resource path not provided (or empty)")
        #return self.delete_doc(*args, subresource_path=subresource_path, **kwargs)
        return self.delete_doc(*args, **kwargs)

    def create_git_action_for_new_illustration(self, new_illustration_id=None):
        '''Checks out master branch of the shard as a side effect'''
        return self._growing_shard.create_git_action_for_new_illustration(new_illustration_id=new_illustration_id)

    def add_new_illustration(self,
                             owner_id,
                             json_repr,
                             auth_info,
                             illustration_id=None,
                             commit_msg=''):
        """Validate and save this JSON. Ensure (and return) a unique illustration id"""
        illustration = self._coerce_json_to_illustration(json_repr)
        if illustration is None:
            msg = "File failed to parse as JSON:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not self._is_valid_illustration_json(illustration):
            msg = "JSON is not a valid illustration:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if illustration_id:
            # try to use this id
            found_owner_id, slug = illustration_id.split('/')
            assert found_owner_id == owner_id
        else:
            # extract a working title and "slugify" it
            slug = self._slugify_internal_illustration_name(json_repr)
            illustration_id = '{i}/{s}'.format(i=owner_id, s=slug)
        # Check the proposed id for uniqueness in any case. Increment until
        # we have a new id, then "reserve" it using a placeholder value.
        with self._index_lock:
            while illustration_id in self._doc2shard_map:
                illustration_id = increment_slug(illustration_id)
            self._doc2shard_map[illustration_id] = None
        # pass the id and collection JSON to a proper git action
        new_illustration_id = None
        r = None
        try:
            # assign the new id to a shard (important prep for commit_and_try_merge2master)
            gd_id_pair = self.create_git_action_for_new_illustration(new_illustration_id=illustration_id)
            new_illustration_id = gd_id_pair[1]
            try:
                # let's remove the 'url' field; it will be restored when the doc is fetched (via API)
                if 'metadata' in illustration and 'url' in illustration['metadata']:
                    del illustration['metadata']['url']
                # it's already been validated, so keep it simple
                r = self.commit_and_try_merge2master(file_content=illustration,
                                                     doc_id=new_illustration_id,
                                                     auth_info=auth_info,
                                                     parent_sha=None,
                                                     commit_msg=commit_msg,
                                                     merged_sha=None)
            except:
                self._growing_shard.delete_doc_from_index(new_illustration_id)
                raise

        except:
            with self._index_lock:
                if new_illustration_id in self._doc2shard_map:
                    del self._doc2shard_map[new_illustration_id]
            raise
        with self._index_lock:
            self._doc2shard_map[new_illustration_id] = self._growing_shard
        return new_illustration_id, r

    def update_existing_illustration(self,
                                     illustration_id=None,
                                     json_repr=None,
                                     auth_info=None,
                                     parent_sha=None,
                                     merged_sha=None,
                                     commit_msg=''):
        """Validate and save this JSON. Ensure (and return) a unique illustration id"""
        illustration = self._coerce_json_to_illustration(json_repr)
        if illustration is None:
            msg = "File failed to parse as JSON:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not self._is_valid_illustration_json(illustration):
            msg = "JSON is not a valid illustration:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not illustration_id:
            raise ValueError("Illustration id not provided (or invalid)")
        if not self.has_doc(illustration_id):
            msg = "Unexpected illustration id '{}' (expected an existing id!)".format(illustration_id)
            raise ValueError(msg)
        # pass the id and illustration JSON to a proper git action
        r = None
        try:
            # remove any 'url' field before saving; it will be restored when the doc is fetched (via API)
            if 'metadata' in illustration and 'url' in illustration['metadata']:
                del illustration['metadata']['url']
            # it's already been validated, so keep it simple
            r = self.commit_and_try_merge2master(file_content=illustration,
                                                 doc_id=illustration_id,
                                                 auth_info=auth_info,
                                                 parent_sha=parent_sha,
                                                 commit_msg=commit_msg,
                                                 merged_sha=merged_sha)
            # identify shard for this id!?
        except:
            raise
        return r

    def get_subresource_list_for_illustration_id(self, illustration_id):
        """Return a list of any files found in this illustration's folder, *except* for the main JSON file"""
        local_path_to_illustration = self._get_illustration_folder(illustration_id)
        _LOG.warn('get_subresource_list_for_illustration_id( {} ): local_path_to_illustration: [{}]'.format(illustration_id, local_path_to_illustration))
        # TODO: Return a more comprehensive dict, with paths as keys? if so, rename 
        # to `get_subresource_info_for_illustration_id`
        return [os.path.join(path, file).replace(local_path_to_illustration + os.path.sep, '')
                for (path, dirs, files) in os.walk(local_path_to_illustration)
                for file in files]

    def retrieve_illustration_subresource(self, illustration_id=None, subresource_path=None, commit_sha=None):
        """Find the specified sub-resource (e.g. a font or image file) and return its filesystem path"""
        if subresource_path.startswith('/'):
            # trim any initial slash, or os.path.join will be confused
            subresource_path = subresource_path[1:]
        # TODO: use commit_sha to retrieve an older version?
        local_path_to_illustration = self._get_illustration_folder(illustration_id)
        _LOG.warn('local_path_to_illustration: [{}]'.format(local_path_to_illustration))
        # look for the named resource in the illustration's folder
        subresource_path = os.path.join(local_path_to_illustration, subresource_path)
        _LOG.warn('FULL LOCAL subresource_path: [{}]'.format(subresource_path))
        if not os.path.exists(subresource_path):
            raise ValueError('Expected subresource not found: {}'.format(subresource_path))
        return subresource_path

    def create_illustration_archive(self, illustration_id=None, commit_sha=None):
        """Create a ZIP archive of the specified illustration's folder. Return its complete path + filename."""
        # TODO: use commit_sha to archive an older version?
        local_path_to_illustration = self._get_illustration_folder(illustration_id)
        _LOG.debug('> local_path_to_illustration: {}'.format(local_path_to_illustration))
        # compress the entire folder to a ZIP archive (in a stream if possible, vs. a file)
        import peyotl
        peyotl_path = os.path.abspath(peyotl.__file__)[0]
        _LOG.debug('> peyotl_path: {}'.format(peyotl_path))
        # use a prepared scratch directory
        # TODO: Consider using python's tempfile module instead? see https://pymotw.com/2/tempfile/
        scratch_dir = os.path.join(peyotl_path, '../scratch/zipped_docs/')
        _LOG.debug('> scratch_dir: {}'.format(scratch_dir))
        scratch_dir = os.path.normpath(scratch_dir)  # remove '../' for safety
        _LOG.debug('> NORMPATH scratch_dir: {}'.format(scratch_dir))
        try:
            assert os.path.isdir(scratch_dir)
        except:
            raise ValueError('Expected scratch directory not found: {}'.format(scratch_dir))
        archive_path_and_name = os.path.join(scratch_dir, illustration_id)
        # N.B. this should clobber any existing archive file by this name!
        new_file = shutil.make_archive(archive_path_and_name, 'zip', root_dir=local_path_to_illustration, base_dir=local_path_to_illustration)
        expected_file = archive_path_and_name +'.zip'
        try:
            assert new_file == expected_file
        except:
            raise ValueError('Expected file not created! Found: [{f}], Expected: [{e}]'.format(found=new_file, expected=expected_file))
        # return the the path+filename
        return new_file

    def _get_illustration_folder(self, illustration_id):
        """Find and return the path to this illustration's folder in local filesystem"""
        if not self._is_valid_illustration_id(illustration_id):
            raise ValueError("Illustration id not provided (or invalid)")
        if not self.has_doc(illustration_id):
            msg = "Unexpected illustration id '{}' (expected an existing id!)".format(illustration_id)
            raise ValueError(msg)
        matching_doc_filepaths = [fp for doc_id, fp in self.iter_doc_filepaths() if doc_id == illustration_id]
        if len(matching_doc_filepaths) > 1:
            msg = "Multiple illustrations found with id '{}' (expected just one!)".format(illustration_id)
            raise ValueError(msg)
        if len(matching_doc_filepaths) == 0:
            msg = "No illustration found with id '{}'!".format(illustration_id)
            raise ValueError(msg)
        filepath = matching_doc_filepaths[0]
        # trim its main JSON file to yield the main folder path
        return os.path.dirname(filepath)

    def _build_illustration_id(self, json_repr):
        """Parse the JSON, return a slug in the form '{subtype}-{first ottid}-{last-ottid}'."""
        illustration = self._coerce_json_to_illustration(json_repr)
        if illustration is None:
            return None
        return slugify('TODO')

    def _slugify_internal_illustration_name(self, json_repr):
        """Parse the JSON, find its name, return a slug of its name"""
        illustration = self._coerce_json_to_illustration(json_repr)
        if illustration is None:
            return None
        internal_name = illustration['metadata']['name']
        return slugify(internal_name)

    def _is_valid_illustration_id(self, test_id):
        """Test for the expected format '{TODO}-{TODO}', return T/F
        N.B. This does not test for a working GitHub username!"""
        return bool(ILLUSTRATION_ID_PATTERN.match(test_id))

    def _is_existing_id(self, test_id):
        """Test to see if this id is non-unique (already exists in a shard)"""
        return test_id in self.get_illustration_ids()

    def _is_valid_illustration_json(self, json_repr):
        """Call the primary validator for a quick test"""
        illustration = self._coerce_json_to_illustration(json_repr)
        if illustration is None:
            # invalid JSON, definitely broken
            return False
        aa = validate_illustration(illustration)
        errors = aa[0]
        for e in errors:
            _LOG.debug('> invalid JSON: {m}'.format(m=e.encode('utf-8')))
        if len(errors) > 0:
            return False
        return True

    def _coerce_json_to_illustration(self, json_repr):
        """Use to ensure that a JSON string (if found) is parsed to the equivalent dict in python.
        If the incoming value is already parsed, do nothing. If a string fails to parse, return None."""
        if isinstance(json_repr, dict):
            illustration = json_repr
        else:
            try:
                illustration = anyjson.loads(json_repr)
            except:
                _LOG.warn('> invalid JSON (failed anyjson parsing)')
                return None
        return illustration

_THE_ILLUSTRATION_STORE = None
def IllustrationStore(repos_dict=None,
                      repos_par=None,
                      with_caching=True,
                      assumed_doc_version=None,
                      git_ssh=None,
                      pkey=None,
                      git_action_class=IllustrationsGitAction,
                      mirror_info=None,
                      infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>'):
    '''Factory function for a _IllustrationStore object.

    A wrapper around the _IllustrationStore class instantiation for
    the most common use case: a singleton _IllustrationStore.
    If you need distinct _IllustrationStore objects, you'll need to
    call that class directly.
    '''
    global _THE_ILLUSTRATION_STORE
    if _THE_ILLUSTRATION_STORE is None:
        _THE_ILLUSTRATION_STORE = _IllustrationStore(repos_dict=repos_dict,
                                                     repos_par=repos_par,
                                                     with_caching=with_caching,
                                                     assumed_doc_version=assumed_doc_version,
                                                     git_ssh=git_ssh,
                                                     pkey=pkey,
                                                     git_action_class=git_action_class,
                                                     mirror_info=mirror_info,
                                                     infrastructure_commit_author=infrastructure_commit_author)
    return _THE_ILLUSTRATION_STORE

