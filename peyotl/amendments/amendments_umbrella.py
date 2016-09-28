# An amendment id should be a unique string (a valid filename) built from a
# range of new taxon ids, in the form '{first_new_ottid}-{last_new_ottid}'.
#     EXAMPLES: 'additions-8783730-8783738'
#               'additions-4999718-5003245'
#               'additions-9998974-10000005'
# N.B. We will somebay bump to 8 digits, so sorting logic should manage this.
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
from peyotl.amendments.amendments_shard import TaxonomicAmendmentsShardProxy, \
                                               TaxonomicAmendmentsShard

from peyotl.amendments.validation import validate_amendment
from peyotl.amendments.git_actions import TaxonomicAmendmentsGitAction
#from peyotl.phylesystem.git_workflows import commit_and_try_merge2master, \
#                                             delete_study, \
#                                             validate_and_convert_nexson
#from peyotl.nexson_validation import ot_validate
import re

# Allow simple slug-ified string with '{known-prefix}-{7-or-8-digit-id}-{7-or-8-digit-id}'
# (8-digit ottids are probably years away, but allow them to be safe.)
# N.B. currently only the 'additions' prefix is supported!
AMENDMENT_ID_PATTERN = re.compile(r'^(additions|changes|deletions)-[0-9]{7,8}-[0-9]{7,8}$')

_LOG = get_logger(__name__)

def prefix_from_amendment_path(amendment_id):
    # The amendment id is in the form '{subtype}-{first ottid}-{last-ottid}'
    #   EXAMPLE: 'additions-0000000-0000005'
    # TODO: Perhaps subtype could work as a prefix? Implies that we'd assign all matching
    # amendments to a single shard.for grouping in shards. Let's try it and see...
    _LOG.debug('> prefix_from_amendment_path(), testing this id: {i}'.format(i=amendment_id))
    id_parts = amendment_id.split('-')
    _LOG.debug('> prefix_from_amendment_path(), found {} parts'.format(len(id_parts)))
    if len(id_parts) > 1:
        subtype = id_parts[0]
    else:
        subtype = 'unknown_subtype'   # or perhaps None?
    return subtype

class TaxonomicAmendmentStoreProxy(ShardedDocStore):
    '''Proxy for interacting with external resources if given the configuration of a remote TaxonomicAmendmentStore
    '''
    def __init__(self, config):
        ShardedDocStore.__init__(self,
                                 prefix_from_doc_id=prefix_from_amendment_path)
        for s in config.get('shards', []):
            self._shards.append(TaxonomicAmendmentsShardProxy(s))
        d = {}
        for s in self._shards:
            for k in s.doc_index.keys():
                if k in d:
                    raise KeyError('Amendment "{i}" found in multiple repos'.format(i=k))
                d[k] = s
        self._doc2shard_map = d

class _TaxonomicAmendmentStore(TypeAwareDocStore):
    '''Wrapper around a set of sharded git repos.
    '''
    def __init__(self,
                 repos_dict=None,
                 repos_par=None,
                 with_caching=True,
                 assumed_doc_version=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=TaxonomicAmendmentsGitAction,
                 mirror_info=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        '''
        Repos can be found by passing in a `repos_par` (a directory that is the parent of the repos)
            or by trusting the `repos_dict` mapping of name to repo filepath.
        `with_caching` should be True for non-debugging uses.
        `assumed_doc_version` is optional. If specified all TaxonomicAmendmentsShard repos are assumed to store
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
                                   prefix_from_doc_id=prefix_from_amendment_path,
                                   repos_dict=repos_dict,
                                   repos_par=repos_par,
                                   with_caching=with_caching,
                                   assumed_doc_version=assumed_doc_version,
                                   git_ssh=git_ssh,
                                   pkey=pkey,
                                   git_action_class=TaxonomicAmendmentsGitAction,
                                   git_shard_class=TaxonomicAmendmentsShard,
                                   mirror_info=mirror_info,
                                   new_doc_prefix=None,
                                   infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                                   **kwargs)
        self._growing_shard._determine_next_ott_id()

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def get_amendment_ids(self):
        return self.get_doc_ids
    @property
    def delete_amendment(self):
        return self.delete_doc

    def create_git_action_for_new_amendment(self, new_amendment_id=None):
        '''Checks out master branch of the shard as a side effect'''
        return self._growing_shard.create_git_action_for_new_amendment(new_amendment_id=new_amendment_id)

    def add_new_amendment(self,
                          json_repr,
                          auth_info,
                          commit_msg=''):
        """Validate and save this JSON. Ensure (and return) a unique amendment id"""
        amendment = self._coerce_json_to_amendment(json_repr)
        if amendment is None:
            msg = "File failed to parse as JSON:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not self._is_valid_amendment_json(amendment):
            msg = "JSON is not a valid amendment:\n{j}".format(j=json_repr)
            raise ValueError(msg)

        # Mint any needed ottids, update the document accordingly, and
        # prepare a response with
        #  - per-taxon mapping of tag to ottid
        #  - resulting id (or URL) to the stored amendment
        # To ensure synchronization of ottids and amendments, this should be an
        # atomic operation!

        # check for tags and confirm count of new ottids required (if provided)
        num_taxa_eligible_for_ids = 0
        for taxon in amendment.get("taxa"):
            # N.B. We don't require 'tag' in amendment validation; check for it now!
            if not "tag" in taxon:
                raise KeyError('Requested Taxon is missing "tag" property!')
            # allow for taxa that have already been assigned (use cases?)
            if not "ott_id" in taxon:
                num_taxa_eligible_for_ids += 1
        if 'new_ottids_required' in amendment:
            requested_ids = amendment['new_ottids_required']
            try:
                assert (requested_ids == num_taxa_eligible_for_ids)
            except:
                raise ValueError('Number of OTT ids requested ({r}) does not match eligible taxa ({t})'.format(r=requested_ids, t=num_taxa_eligible_for_ids))

        # mint new ids and assign each to an eligible taxon
        with self._growing_shard._doc_counter_lock:
            # build a map of tags to ottids, to return to the caller
            tag_to_id = {}
            first_new_id = self._growing_shard.next_ott_id
            last_new_id = first_new_id + num_taxa_eligible_for_ids - 1
            if last_new_id < first_new_id:
                # This can happen if ther are no eligible taxa! In this case,
                # repeat and "burn" the next ottid (ie, it will be used to
                # identify this amendment, but it won't be assigned)
                last_new_id = first_new_id
            new_id = first_new_id
            for taxon in amendment.get("taxa"):
                if not "ott_id" in taxon:
                    taxon["ott_id"] = new_id
                    ttag = taxon["tag"]
                    tag_to_id[ttag] = new_id
                    new_id += 1
                    ptag = taxon.get("parent_tag")
                    if ptag != None:
                        taxon["parent"] = tag_to_id[ptag]
            if num_taxa_eligible_for_ids > 0:
                try:
                    assert (new_id == (last_new_id + 1))
                except:
                    applied = last_new_id - first_new_id + 1
                    raise ValueError('Number of OTT ids requested ({r}) does not match ids actually applied ({a})'.format(r=requested_ids, a=applied))

            # Build a proper amendment id, in the format '{subtype}-{first ottid}-{last-ottid}'
            amendment_subtype = 'additions'
            # TODO: Handle other subtypes (beyond additions) by examining JSON?
            amendment_id = "{s}-{f}-{l}".format(s=amendment_subtype, f=first_new_id, l=last_new_id)

            # Check the proposed id for uniqueness (just to be safe), then
            # "reserve" it using a placeholder value.
            with self._index_lock:
                if amendment_id in self._doc2shard_map:
                    # this should never happen!
                    raise KeyError('Amendment "{i}" already exists!'.format(i=amendment_id))
                self._doc2shard_map[amendment_id] = None

            # Set the amendment's top-level "id" property to match
            amendment["id"] = amendment_id

            # pass the id and amendment JSON to a proper git action
            new_amendment_id = None
            r = None
            try:
                # assign the new id to a shard (important prep for commit_and_try_merge2master)
                gd_id_pair = self.create_git_action_for_new_amendment(new_amendment_id=amendment_id)
                new_amendment_id = gd_id_pair[1]
                # For amendments, the id should not have changed!
                try:
                    assert new_amendment_id == amendment_id
                except:
                    raise KeyError('Amendment id unexpectedly changed from "{o}" to "{n}"!'.format(
                              o=amendment_id, n=new_amendment_id))
                try:
                    # it's already been validated, so keep it simple
                    r = self.commit_and_try_merge2master(file_content=amendment,
                                                         doc_id=new_amendment_id,
                                                         auth_info=auth_info,
                                                         parent_sha=None,
                                                         commit_msg=commit_msg,
                                                         merged_sha=None)
                except:
                    self._growing_shard.delete_doc_from_index(new_amendment_id)
                    raise

                # amendment is now in the repo, so we can safely reserve the ottids
                first_minted_id, last_minted_id = self._growing_shard._mint_new_ott_ids(
                    how_many=max(num_taxa_eligible_for_ids,1))
                # do a final check for errors!
                try:
                    assert first_minted_id == first_new_id
                except:
                    raise ValueError('First minted ottid is "{m}", expected "{e}"!'.format(
                        m=first_minted_id, e=first_new_id))
                try:
                    assert last_minted_id == last_new_id
                except:
                    raise ValueError('Last minted ottid is "{m}", expected "{e}"!'.format(
                        m=last_minted_id, e=last_new_id))
                # Add the tag-to-ottid mapping to the response, so a caller
                # (e.g. the curation webapp) can provisionally assign them
                r['tag_to_ottid'] = tag_to_id
            except:
                with self._index_lock:
                    if new_amendment_id in self._doc2shard_map:
                        del self._doc2shard_map[new_amendment_id]
                raise

        with self._index_lock:
            self._doc2shard_map[new_amendment_id] = self._growing_shard
        return new_amendment_id, r

    def update_existing_amendment(self,
                                  amendment_id=None,
                                  json_repr=None,
                                  auth_info=None,
                                  parent_sha=None,
                                  merged_sha=None,
                                  commit_msg=''):
        """Validate and save this JSON. Ensure (and return) a unique amendment id"""
        amendment = self._coerce_json_to_amendment(json_repr)
        if amendment is None:
            msg = "File failed to parse as JSON:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not self._is_valid_amendment_json(amendment):
            msg = "JSON is not a valid amendment:\n{j}".format(j=json_repr)
            raise ValueError(msg)
        if not amendment_id:
            raise ValueError("Amendment id not provided (or invalid)")
        if not self.has_doc(amendment_id):
            msg = "Unexpected amendment id '{}' (expected an existing id!)".format(amendment_id)
            raise ValueError(msg)
        # pass the id and amendment JSON to a proper git action
        r = None
        try:
            # it's already been validated, so keep it simple
            r = self.commit_and_try_merge2master(file_content=amendment,
                                                 doc_id=amendment_id,
                                                 auth_info=auth_info,
                                                 parent_sha=parent_sha,
                                                 commit_msg=commit_msg,
                                                 merged_sha=merged_sha)
            # identify shard for this id!?
        except:
            raise
        return r

    def _build_amendment_id(self, json_repr):
        """Parse the JSON, return a slug in the form '{subtype}-{first ottid}-{last-ottid}'."""
        amendment = self._coerce_json_to_amendment(json_repr)
        if amendment is None:
            return None
        amendment_subtype = 'additions'
        # TODO: Look more deeply once we have other subtypes!
        first_ottid = amendment['TODO']
        last_ottid = amendment['TODO']
        return slugify('{s}-{f}-{l}'.format(s=amendment_subtype, f=first_ottid, l=last_ottid))

    def _is_valid_amendment_id(self, test_id):
        """Test for the expected format '{subtype}-{first ottid}-{last-ottid}', return T/F
        N.B. This does not test for a working GitHub username!"""
        return bool(AMENDMENT_ID_PATTERN.match(test_id))

    def _is_existing_id(self, test_id):
        """Test to see if this id is non-unique (already exists in a shard)"""
        return test_id in self.get_amendment_ids()

    def _is_valid_amendment_json(self, json_repr):
        """Call the primary validator for a quick test"""
        amendment = self._coerce_json_to_amendment(json_repr)
        if amendment is None:
            # invalid JSON, definitely broken
            return False
        aa = validate_amendment(amendment)
        errors = aa[0]
        for e in errors:
            _LOG.debug('> invalid JSON: {m}'.format(m=e.encode('utf-8')))
        if len(errors) > 0:
            return False
        return True

    def _coerce_json_to_amendment(self, json_repr):
        """Use to ensure that a JSON string (if found) is parsed to the equivalent dict in python.
        If the incoming value is already parsed, do nothing. If a string fails to parse, return None."""
        if isinstance(json_repr, dict):
            amendment = json_repr
        else:
            try:
                amendment = anyjson.loads(json_repr)
            except:
                _LOG.warn('> invalid JSON (failed anyjson parsing)')
                return None
        return amendment

_THE_TAXONOMIC_AMENDMENT_STORE = None
def TaxonomicAmendmentStore(repos_dict=None,
                            repos_par=None,
                            with_caching=True,
                            assumed_doc_version=None,
                            git_ssh=None,
                            pkey=None,
                            git_action_class=TaxonomicAmendmentsGitAction,
                            mirror_info=None,
                            infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>'):
    '''Factory function for a _TaxonomicAmendmentStore object.

    A wrapper around the _TaxonomicAmendmentStore class instantiation for
    the most common use case: a singleton _TaxonomicAmendmentStore.
    If you need distinct _TaxonomicAmendmentStore objects, you'll need to
    call that class directly.
    '''
    global _THE_TAXONOMIC_AMENDMENT_STORE
    if _THE_TAXONOMIC_AMENDMENT_STORE is None:
        _THE_TAXONOMIC_AMENDMENT_STORE = _TaxonomicAmendmentStore(repos_dict=repos_dict,
                                                                  repos_par=repos_par,
                                                                  with_caching=with_caching,
                                                                  assumed_doc_version=assumed_doc_version,
                                                                  git_ssh=git_ssh,
                                                                  pkey=pkey,
                                                                  git_action_class=git_action_class,
                                                                  mirror_info=mirror_info,
                                                                  infrastructure_commit_author=infrastructure_commit_author)
    return _THE_TAXONOMIC_AMENDMENT_STORE

