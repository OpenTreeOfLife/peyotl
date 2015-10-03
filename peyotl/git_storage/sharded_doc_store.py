"""Base class for sharded document storage (for phylesystem, tree collections, etc.)
N.B. that this class has no knowledge of different document types. It provides
basic functionality common to minimal *Proxy classes with remote shards, and
more full-featured subclasses based on TypeAwareDocStore.
"""
from threading import Lock

class ShardedDocStore(object):
    '''Shared functionality for PhylesystemBase, TreeCollectionStoreBase, etc.
    We'll use 'doc' here to refer to a single object of interest (eg, a study or
    tree collection) in the collection.

    N.B. In current subclasses, each docstore has one main document type, and
    each document is stored as a single file in git. Watch for complications if
    either of these assumptions is challenged for a new type!
    '''
    def __init__(self, prefix_from_doc_id=None):
        self._index_lock = Lock()
        self._shards = []
        self._doc2shard_map = {}
        self._prefix2shard = {}
        # We assume that consistent doc-id prefixes are used to keep like data
        # in the same shard. Each subclass has its own rules for these.
        self.prefix_from_doc_id = prefix_from_doc_id
    def get_repo_and_path_fragment(self, doc_id):
        '''For `doc_id` returns a list of:
            [0] the repo name and,
            [1] the path from the repo to the doc file.
        This is useful because
        (if you know the remote), it lets you construct the full path.
        '''
        shard = self.get_shard(doc_id)
        return shard.name, shard.get_rel_path_fragment(doc_id)
    def get_public_url(self, doc_id, branch='master'):
        '''Returns a GitHub URL for the doc in question (study, collection, ...)
        '''
        name, path_frag = self.get_repo_and_path_fragment(doc_id)
        return 'https://raw.githubusercontent.com/OpenTreeOfLife/' + name + '/' + branch + '/' + path_frag
    get_external_url = get_public_url
    def _doc_merged_hook(self, ga, doc_id):
        with self._index_lock:
            if doc_id in self._doc2shard_map:
                return
        # this lookup has to be outside of the lock-holding part to avoid deadlock
        shard = self.get_shard(doc_id)
        with self._index_lock:
            self._doc2shard_map[doc_id] = shard
        try:
            shard.register_doc_id(ga, doc_id)
        except AttributeError:
            pass
    def get_shard(self, doc_id):
        try:
            with self._index_lock:
                return self._doc2shard_map[doc_id]
        except KeyError:
            # Look up the shard where the doc should be (in case it was
            #   deleted. This fall back relies on a unique prefix for each shard)
            pref = self.prefix_from_doc_id(doc_id)
            try:
                return self._prefix2shard[pref]
            except KeyError:
                # it's a new prefix! return the latest ("growing") shard
                return self._shards[-1]
    def get_doc_ids(self):
        k = []
        for shard in self._shards:
            k.extend(shard.get_doc_ids())
        return k


