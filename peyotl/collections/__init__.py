 #!/usr/bin/env python
'''Basic functions for creating and manipulating collection JSON.
'''

def get_empty_collection():
    collection = {
        "url": "",
        "name": "",
        "description": "",
        "creator": {"login": "", "name": ""},
        "contributors": [ ],
        "decisions": [ ],
        "queries": [ ]
    }
    return collection

__all__ = [#'git_actions',
           #'git_workflows',
           #'helper',
           #'collections_shard',
           'collections_umbrella']
from peyotl.collections.collections_umbrella import TreeCollectionStore, TreeCollectionStoreProxy
