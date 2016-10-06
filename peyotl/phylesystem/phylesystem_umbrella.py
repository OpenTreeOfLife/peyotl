from peyotl.utility import get_logger, \
    get_config_setting
try:
    from dogpile.cache.api import NO_VALUE
except:
    pass #caching is optional
from peyotl.phylesystem.helper import _make_phylesystem_cache_region
from peyotl.git_storage import ShardedDocStore, \
                               TypeAwareDocStore
from peyotl.phylesystem.phylesystem_shard import PhylesystemShardProxy, \
                                                 PhylesystemShard
from peyotl.phylesystem.git_actions import PhylesystemGitAction
from peyotl.phylesystem.git_workflows import validate_and_convert_nexson
from peyotl.nexson_validation import ot_validate
from peyotl.nexson_validation._validation_base import NexsonAnnotationAdder, \
                                                      replace_same_agent_annotation
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
        self.repo_nexml2json = config.get('repo_nexml2json', None)
        if self.repo_nexml2json is None:
            # TODO: remove this fallback for older remote phylesystem config
            self.repo_nexml2json = config.get('assumed_doc_version', None)
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
                 git_action_class=PhylesystemGitAction,
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
        `git_action_class` is a subclass of GitActionBase to use. the __init__ syntax must be compatible
            with PhylesystemGitAction
        If you want to use a mirrors of the repo for pushes or pulls, send in a `mirror_info` dict:
            mirror_info['push'] and mirror_info['pull'] should be dicts with the following keys:
            'parent_dir' - the parent directory of the mirrored repos
            'remote_map' - a dictionary of remote name to prefix (the repo name + '.git' will be
                appended to create the URL for pushing).
        '''
        self._new_study_prefix = None
        TypeAwareDocStore.__init__(self,
                                   prefix_from_doc_id=prefix_from_study_id,
                                   repos_dict=repos_dict,
                                   repos_par=repos_par,
                                   with_caching=with_caching,
                                   assumed_doc_version=repo_nexml2json,
                                   git_ssh=git_ssh,
                                   pkey=pkey,
                                   git_action_class=PhylesystemGitAction,
                                   git_shard_class=PhylesystemShard,
                                   mirror_info=mirror_info,
                                   new_doc_prefix=new_study_prefix,
                                   infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                                   **kwargs)
        self._new_study_prefix = self._growing_shard._new_study_prefix  # TODO:shard-edits?
        self._growing_shard._determine_next_study_id()
        if with_caching:
            self._cache_region = _make_phylesystem_cache_region()
        else:
            self._cache_region = None
        self._cache_hits = 0

    def get_study_ids(self, include_aliases=False):
        k = []
        for shard in self._shards:
            k.extend(shard.get_study_ids(include_aliases=include_aliases))
        return k

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def return_study(self):
        return self.return_doc
    @property
    def get_changed_studies(self):
        return self.get_changed_docs
    @property
    def push_study_to_remote(self):
        return self.push_doc_to_remote
    @property
    def iter_study_objs(self):
        return self.iter_doc_objs
    @property
    def iter_study_filepaths(self):
        return self.iter_doc_filepaths

    @property
    def new_study_prefix(self):
        return self.new_doc_prefix
    @new_study_prefix.setter
    def new_study_prefix(self, val):
        self.new_doc_prefix = val

    @property
    def get_blob_sha_for_study_id(self):
        return self.get_blob_sha_for_doc_id
    @property
    def get_version_history_for_study_id(self):
        return self.get_version_history_for_doc_id
    @property
    def delete_study(self):
        return self.delete_doc

    @property
    def repo_nexml2json(self):
        return self.assumed_doc_version
    @repo_nexml2json.setter
    def repo_nexml2json(self, val):
        self.assumed_doc_version = val

    def _mint_new_study_id(self):
        '''Checks out master branch of the shard as a side effect'''
        return self._growing_shard._mint_new_study_id()

    def create_git_action_for_new_study(self, new_study_id=None):
        '''Checks out master branch of the shard as a side effect'''
        return self._growing_shard.create_git_action_for_new_study(new_study_id=new_study_id)

    def ingest_new_study(self,
                         new_study_nexson,
                         repo_nexml2json,
                         auth_info,
                         new_study_id=None):
        placeholder_added = False
        if new_study_id is not None:
            if new_study_id.startswith(self._new_study_prefix):
                m = 'Document IDs with the "{}" prefix can only be automatically generated.'
                m = m.format(self._new_study_prefix)
                raise ValueError(m)
            if not STUDY_ID_PATTERN.match(new_study_id):
                raise ValueError('Document ID does not match the expected pattern of alphabeticprefix_numericsuffix')
            with self._index_lock:
                if new_study_id in self._doc2shard_map:
                    raise ValueError('Document ID is already in use!')
                self._doc2shard_map[new_study_id] = None
                placeholder_added = True
        try:
            gd, new_study_id = self.create_git_action_for_new_study(new_study_id=new_study_id)
            try:
                nexml = new_study_nexson['nexml']
                nexml['^ot:studyId'] = new_study_id
                bundle = validate_and_convert_nexson(new_study_nexson,
                                                     repo_nexml2json,
                                                     allow_invalid=True)
                nexson, annotation, nexson_adaptor = bundle[0], bundle[1], bundle[3]
                r = self.annotate_and_write(git_data=gd,
                                            nexson=nexson,
                                            doc_id=new_study_id,
                                            auth_info=auth_info,
                                            adaptor=nexson_adaptor,
                                            annotation=annotation,
                                            parent_sha=None,
                                            master_file_blob_included=None)
            except:
                self._growing_shard.delete_doc_from_index(new_study_id)
                raise
        except:
            if placeholder_added:
                with self._index_lock:
                    if new_study_id in self._doc2shard_map:
                        del self._doc2shard_map[new_study_id]
            raise
        with self._index_lock:
            self._doc2shard_map[new_study_id] = self._growing_shard
        return new_study_id, r

    def add_validation_annotation(self, doc_obj, sha):
        need_to_cache = False
        adaptor = None
        if self._cache_region is not None:
            key = 'v' + sha
            annot_event = self._cache_region.get(key, ignore_expiration=True)
            if annot_event != NO_VALUE:
                _LOG.debug('cache hit for ' + key)
                adaptor = NexsonAnnotationAdder()
                self._cache_hits += 1
            else:
                _LOG.debug('cache miss for ' + key)
                need_to_cache = True
        if adaptor is None:
            bundle = ot_validate(doc_obj)
            annotation = bundle[0]
            annot_event = annotation['annotationEvent']
            #del annot_event['@dateCreated'] #TEMP
            #del annot_event['@id'] #TEMP
            adaptor = bundle[2]
        replace_same_agent_annotation(doc_obj, annot_event)
        if need_to_cache:
            self._cache_region.set(key, annot_event)
            _LOG.debug('set cache for ' + key)
        return annot_event

    def write_configuration(self, out, secret_attrs=False):
        """Type-specific configuration for backward compatibility"""
        key_order = ['repo_nexml2json',
                     'number_of_shards',
                     'initialization',]
        cd = self.get_configuration_dict(secret_attrs=secret_attrs)
        for k in key_order:
            if k in cd:
                out.write('  {} = {}'.format(k, cd[k]))
        for n, shard in enumerate(self._shards):
            out.write('Shard {}:\n'.format(n))
            shard.write_configuration(out)
    def get_configuration_dict(self, secret_attrs=False):
        """Type-specific configuration for backward compatibility"""
        cd = {'repo_nexml2json': self.repo_nexml2json,
              'number_of_shards': len(self._shards),
              'initialization': self._filepath_args}
        cd['shards'] = []
        for i in self._shards:
            cd['shards'].append(i.get_configuration_dict(secret_attrs=secret_attrs))
        return cd

_THE_PHYLESYSTEM = None
def Phylesystem(repos_dict=None,
                repos_par=None,
                with_caching=True,
                repo_nexml2json=None,
                git_ssh=None,
                pkey=None,
                git_action_class=PhylesystemGitAction,
                mirror_info=None,
                new_study_prefix=None,
                infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>'):
    '''Factory function for a _Phylesystem object.

    A wrapper around the _Phylesystem class instantiation for
    the most common use case: a singleton _Phylesystem.
    If you need distinct _Phylesystem objects, you'll need to
    call that class directly.
    '''
    if not repo_nexml2json:
        repo_nexml2json = get_config_setting('phylesystem', 'repo_nexml2json')
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

