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

# TODO: An illustration id should be a unique string (a valid filename) built from...
ILLUSTRATION_ID_PATTERN = re.compile(r'^TODO$')

_LOG = get_logger(__name__)

def prefix_from_illustration_path(illustration_id):
    # TODO: Determine the format/pattern for illustration ids!
    _LOG.debug('> prefix_from_illustration_path(), testing this id: {i}'.format(i=illustration_id))
    return ''

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
        self._growing_shard._determine_next_ott_id()

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def get_illustration_ids(self):
        return self.get_doc_ids
    @property
    def delete_illustration(self):
        return self.delete_doc

    def create_git_action_for_new_illustration(self, new_illustration_id=None):
        '''Checks out master branch of the shard as a side effect'''
        return self._growing_shard.create_git_action_for_new_illustration(new_illustration_id=new_illustration_id)

    def add_new_illustration(self,
                          json_repr,
                          auth_info,
                          commit_msg=''):
        """Validate and save this JSON. Ensure (and return) a unique illustration id"""
        illustration = self._coerce_json_to_illustration(json_repr)
        if illustration is None:
            msg = "File failed to parse as JSON:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not self._is_valid_illustration_json(illustration):
            msg = "JSON is not a valid illustration:\n{j}".format(j=json_repr)
            raise ValueError(msg)

        with self._growing_shard._doc_counter_lock:
            # mint any needed ids?
            illustration_id = 'TODO'

            # Check the proposed id for uniqueness (just to be safe), then
            # "reserve" it using a placeholder value.
            with self._index_lock:
                if illustration_id in self._doc2shard_map:
                    # this should never happen!
                    raise KeyError('Illustration "{i}" already exists!'.format(i=illustration_id))
                self._doc2shard_map[illustration_id] = None

            # Set the illustration's top-level "id" property to match
            illustration["id"] = illustration_id

            # pass the id and illustration JSON to a proper git action
            new_illustration_id = None
            r = None
            try:
                # assign the new id to a shard (important prep for commit_and_try_merge2master)
                gd_id_pair = self.create_git_action_for_new_illustration(new_illustration_id=illustration_id)
                new_illustration_id = gd_id_pair[1]
                # For illustrations, the id should not have changed!
                try:
                    assert new_illustration_id == illustration_id
                except:
                    raise KeyError('Illustration id unexpectedly changed from "{o}" to "{n}"!'.format(
                              o=illustration_id, n=new_illustration_id))
                try:
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

    def retrieve_illustration_subresource(self, illustration_id=None, subresource_path=None, commit_sha=None):
        """Find the specified sub-resource (e.g. a font or image file) and return its filesystem path"""
        # TODO: use commit_sha to retrieve an older version?
        local_path_to_illustration = self._get_illustration_folder(illustration_id)
        # look for the named resource in the illustration's folder
        subresource_path = os.path.join(local_path_to_illustration, subresource_path)
        if not os.path.exists(subresource_path):
            raise ValueError('Expected subresource not found: {}'.format(subresource_path))
        return subresource_path

    def create_illustration_archive(self, illustration_id=None, commit_sha=None):
        """Create a ZIP archive of the specified illustration's folder. Return its complete path + filename."""
        # TODO: use commit_sha to archive an older version?
        local_path_to_illustration = self._get_illustration_folder(illustration_id)
        # compress the entire folder to a ZIP archive (in a stream if possible, vs. a file)
        import peyotl
        peyotl_path = os.path.abspath(peyotl.__file__)[0]
        # use a prepared scratch directory
        # TODO: Consider using python's tempfile module instead? see https://pymotw.com/2/tempfile/
        scratch_dir = os.path.join(peyotl_path, '../scratch/zipped_docs/')
        scratch_dir = os.path.normpath(scratch_dir)  # remove '../' for safety
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
        if not _is_valid_illustration_id(illustration_id):
            raise ValueError("Illustration id not provided (or invalid)")
        if not self.has_doc(illustration_id):
            msg = "Unexpected illustration id '{}' (expected an existing id!)".format(illustration_id)
            raise ValueError(msg)
        matching_illustration_paths = [fp for doc_id, fp in self.iter_doc_filepaths() if doc_id == illustration_id]
        if len(matching_illustration_paths) > 1:
            msg = "Multiple illustrations found with id '{}' (expected just one!)".format(illustration_id)
            raise ValueError(msg)
        if len(matching_illustration_paths) == 0:
            msg = "No illustration found with id '{}'!".format(illustration_id)
            raise ValueError(msg)
        return matching_illustration_paths[0]

    def _build_illustration_id(self, json_repr):
        """Parse the JSON, return a slug in the form '{subtype}-{first ottid}-{last-ottid}'."""
        illustration = self._coerce_json_to_illustration(json_repr)
        if illustration is None:
            return None
        return slugify('TODO')

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

