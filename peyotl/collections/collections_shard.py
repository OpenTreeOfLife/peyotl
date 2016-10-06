import os
import codecs
from threading import Lock
from peyotl.utility import get_logger, \
    get_config_setting
from peyotl.git_storage.git_shard import GitShard, \
                                         TypeAwareGitShard, \
                                         _invert_dict_list_val

_LOG = get_logger(__name__)

doc_holder_subpath = 'collections-by-owner'

def filepath_for_collection_id(repo_dir, collection_id):
    # in this case, simply expand the id to a full path
    collection_filename = '{i}.json'.format(i=collection_id)
    full_path_to_file = os.path.join(repo_dir, doc_holder_subpath, collection_filename)
    _LOG.warn(">>>> filepath_for_collection_id: full path is {}".format(full_path_to_file))
    return full_path_to_file

class TreeCollectionsShardProxy(GitShard):
    '''Proxy for shard when interacting with external resources if given the configuration of a remote Phylesystem
    '''
    def __init__(self, config):
        GitShard.__init__(self, config['name'])
        self.assumed_doc_version = config['assumed_doc_version']
        d = {}
        for collection in config['collections']:
            kl = collection['keys']
            if len(kl) > 1:
                self.has_aliases = True
            for k in collection['keys']:
                complete_path = '{p}/{s}/{r}'.format(p=self.path, s=doc_holder_subpath, r=collection['relpath'])
                d[k] = (self.name, self.path, complete_path)
        self.doc_index = d

def create_id2collection_info(path, tag):
    '''Searchers for JSON files in this repo and returns
    a map of collection id ==> (`tag`, dir, collection filepath)
    where `tag` is typically the shard name
    '''
    d = {}
    for triple in os.walk(path):
        root, files = triple[0], triple[2]
        for filename in files:
            if filename.endswith('.json'):
                # trim file extension and prepend owner_id (from path)
                collection_id = "{u}/{n}".format(u=root.split('/')[-1], n=filename[:-5])
                d[collection_id] = (tag, root, os.path.join(root, filename))
    return d

def refresh_collection_index(shard, initializing=False):
    d = create_id2collection_info(shard.doc_dir, shard.name)
    shard.has_aliases = False
    shard._doc_index = d

class TreeCollectionsShard(TypeAwareGitShard):
    '''Wrapper around a git repo holding JSON tree collections
    Raises a ValueError if the directory does not appear to be a TreeCollectionsShard.
    Raises a RuntimeError for errors associated with misconfiguration.'''
    from peyotl.phylesystem.git_actions import PhylesystemGitAction
    def __init__(self,
                 name,
                 path,
                 assumed_doc_version=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=PhylesystemGitAction,
                 push_mirror_repo_path=None,
                 new_doc_prefix=None, # IGNORED in this shard type
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        self.max_file_size = get_config_setting('phylesystem', 'max_file_size')
        TypeAwareGitShard.__init__(self,
                                   name,
                                   path,
                                   doc_holder_subpath,
                                   assumed_doc_version,
                                   None,  # version detection
                                   refresh_collection_index,  # populates _doc_index
                                   git_ssh,
                                   pkey,
                                   git_action_class,
                                   push_mirror_repo_path,
                                   infrastructure_commit_author,
                                   **kwargs)
        self.filepath_for_doc_id_fn = filepath_for_collection_id
        self._doc_counter_lock = Lock()
        self.filepath_for_global_resource_fn = lambda frag: os.path.join(path, frag)

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def known_prefixes(self):
        if self._known_prefixes is None:
            self._known_prefixes = self._diagnose_prefixes()
        return self._known_prefixes


    # Type-specific configuration for backward compatibility
    # (config is visible to API consumers via /phylesystem_config)
    def write_configuration(self, out, secret_attrs=False):
        """Generic configuration, may be overridden by type-specific version"""
        key_order = ['name', 'path', 'git_dir', 'doc_dir', 'assumed_doc_version',
                     'git_ssh', 'pkey', 'has_aliases', 'number of collections']
        cd = self.get_configuration_dict(secret_attrs=secret_attrs)
        for k in key_order:
            if k in cd:
                out.write('  {} = {}'.format(k, cd[k]))
        out.write('  collections in alias groups:\n')
        for o in cd['collections']:
            out.write('    {} ==> {}\n'.format(o['keys'], o['relpath']))
    def get_configuration_dict(self, secret_attrs=False):
        """Overrides superclass method and renames some properties"""
        cd = super(TreeCollectionsShard, self).get_configuration_dict(secret_attrs=secret_attrs)
        # "rename" some keys in the dict provided
        cd['number of collections'] = cd.pop('number of documents')
        cd['collections'] = cd.pop('documents')
        return cd

    def _diagnose_prefixes(self):
        '''Returns a set of all of the prefixes seen in the main document dir
        '''
        from peyotl.collections import COLLECTION_ID_PATTERN
        p = set()
        for owner_dirname in os.listdir(self.doc_dir):
            example_collection_name = "{n}/xxxxx".format(n=owner_dirname)
            if COLLECTION_ID_PATTERN.match(example_collection_name):
                p.add(owner_dirname)
        return p

    def create_git_action_for_new_collection(self, new_collection_id=None):
        '''Checks out master branch as a side effect'''
        ga = self.create_git_action()
        assert new_collection_id is not None
        # id should have been sorted out by the caller
        self.register_doc_id(ga, new_collection_id)
        return ga, new_collection_id

    def _create_git_action_for_global_resource(self):
        return self._ga_class(repo=self.path,
                              git_ssh=self.git_ssh,
                              pkey=self.pkey,
                              path_for_doc_fn=self.filepath_for_global_resource_fn,
                              max_file_size=self.max_file_size)
