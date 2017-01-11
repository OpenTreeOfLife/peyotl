import os
import codecs
from threading import Lock
from peyotl.utility import get_logger, \
                           get_config_setting
from peyotl.git_storage.git_shard import GitShard, \
                                         TypeAwareGitShard, \
                                         _invert_dict_list_val

_LOG = get_logger(__name__)

doc_holder_subpath = 'docs-by-owner'

def folderpath_for_illustration_id(repo_dir, illustration_id):
    # expand the id to a full path, then point to the core JSON file
    illustration_foldername = illustration_id
    full_path_to_folder = os.path.join(repo_dir, doc_holder_subpath, illustration_foldername)
    _LOG.debug(">>>> folderpath_for_illustration_id: full path is {}".format(full_path_to_folder))
    return full_path_to_folder

def main_filepath_for_illustration_id(repo_dir, illustration_id):
    main_folder_path = folderpath_for_illustration_id(repo_dir, illustration_id)
    full_path_to_file = os.path.join(main_folder_path, 'main.json')
    _LOG.warn(">>>> main_filepath_for_illustration_id: full path is {}".format(full_path_to_file))
    return full_path_to_file

class IllustrationsShardProxy(GitShard):
    '''Proxy for shard when interacting with external resources if given the configuration of a remote Phylesystem
    '''
    def __init__(self, config):
        GitShard.__init__(self, config['name'])
        self.assumed_doc_version = config['assumed_doc_version']
        d = {}
        for illustration in config['illustrations']:
            kl = illustration['keys']
            if len(kl) > 1:
                self.has_aliases = True
            for k in illustration['keys']:
                complete_path = '{p}/{s}/{r}'.format(p=self.path, s=doc_holder_subpath, r=illustration['relpath'])
                d[k] = (self.name, self.path, complete_path)
        self.doc_index = d

def create_id2illustration_info(path, tag):
    '''Searches for JSON files in this repo and returns
    a map of illustration id ==> (`tag`, dir, illustration filepath)
    where `tag` is typically the shard name
    '''
    d = {}
    for triple in os.walk(path):
        root, files = triple[0], triple[2]
        if 'main.json' in files:
            # build ID (from path) using owner-id and illustration folder name
            illustration_id = "/".join( root.split('/')[-2:] )
            # point directly to each doc's "manifest" file
            d[illustration_id] = (tag, root, os.path.join(root))
    return d

def refresh_illustration_index(shard, initializing=False):
    d = create_id2illustration_info(shard.doc_dir, shard.name)
    shard.has_aliases = False
    shard._doc_index = d

class IllustrationsShard(TypeAwareGitShard):
    '''Wrapper around a git repo holding folderish tree illustrations
    Raises a ValueError if the directory does not appear to be a IllustrationsShard.
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
                                   refresh_illustration_index,  # populates _doc_index
                                   git_ssh,
                                   pkey,
                                   git_action_class,
                                   push_mirror_repo_path,
                                   infrastructure_commit_author,
                                   **kwargs)
        self.filepath_for_doc_id_fn = main_filepath_for_illustration_id
        self.folderpath_for_doc_id_fn = folderpath_for_illustration_id
        self._doc_counter_lock = Lock()
        self._next_ott_id = None
        self._id_minting_file = os.path.join(path, 'next_ott_id.json')
        # N.B. This is for minting invididual taxon (OTT) ids, not amendment ids!
        # We construct each amendment from its unique series of ottids.
        self.filepath_for_global_resource_fn = lambda frag: os.path.join(path, frag)

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def next_ott_id(self):
        return self._next_ott_id
    @property
    def known_prefixes(self):
        # this is required by TypeAwareDocStore
        if self._known_prefixes is None:
            self._known_prefixes = self._diagnose_prefixes() 
        return self._known_prefixes

    # Type-specific configuration for backward compatibility
    # (config is visible to API consumers via /phylesystem_config)
    def write_configuration(self, out, secret_attrs=False):
        """Generic configuration, may be overridden by type-specific version"""
        key_order = ['name', 'path', 'git_dir', 'doc_dir', 'assumed_doc_version',
                     'git_ssh', 'pkey', 'has_aliases', '_next_ott_id', 
                     'number of illustrations']
        cd = self.get_configuration_dict(secret_attrs=secret_attrs)
        for k in key_order:
            if k in cd:
                out.write('  {} = {}'.format(k, cd[k]))
        out.write('  illustrations in alias groups:\n')
        for o in cd['illustrations']:
            out.write('    {} ==> {}\n'.format(o['keys'], o['relpath']))
    def get_configuration_dict(self, secret_attrs=False):
        """Overrides superclass method and renames some properties"""
        cd = super(IllustrationsShard, self).get_configuration_dict(secret_attrs=secret_attrs)
        # "rename" some keys in the dict provided
        cd['number of illustrations'] = cd.pop('number of documents')
        cd['illustrations'] = cd.pop('documents')
        # add keys particular to this shard subclass
        if self._next_ott_id is not None:
            cd['_next_ott_id'] = self._next_ott_id,
        return cd

    def _diagnose_prefixes(self):
        '''Returns a set of all of the prefixes seen in the main document dir
           (This is currently always empty, since we don't use a prefix for
           naming illustrations.)
        '''
        return set()

    def _mint_new_ott_ids(self, how_many=1):
        ''' ASSUMES the caller holds the _doc_counter_lock !
        Checks the current int value of the next ottid, reserves a block of
        {how_many} ids, advances the counter to the next available value,
        stores the counter in a file in case the server is restarted.
        Checks out master branch as a side effect.'''
        first_minted_id = self._next_ott_id
        self._next_ott_id = first_minted_id + how_many
        content = u'{"next_ott_id": %d}\n' % self._next_ott_id
        # The content is JSON, but we hand-rolled the string above
        #       so that we can use it as a commit_msg
        self._write_master_branch_resource(content,
                                           self._id_minting_file,
                                           commit_msg=content,
                                           is_json=False)
        last_minted_id = self._next_ott_id - 1
        return first_minted_id, last_minted_id

    def create_git_action_for_new_illustration(self, new_illustration_id=None):
        '''Checks out master branch as a side effect'''
        ga = self.create_git_action()
        assert new_illustration_id is not None
        # id should have been sorted out by the caller
        self.register_doc_id(ga, new_illustration_id)
        return ga, new_illustration_id

    def _create_git_action_for_global_resource(self):
        return self._ga_class(repo=self.path,
                              git_ssh=self.git_ssh,
                              pkey=self.pkey,
                              path_for_doc_fn=self.filepath_for_global_resource_fn,
                              max_file_size=self.max_file_size)
