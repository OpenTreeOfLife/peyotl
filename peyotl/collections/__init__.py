 #!/usr/bin/env python
'''Basic functions for creating and manipulating collection JSON.
'''

def get_empty_collection():
    collection = {
        "url": "",
        "name": "",
        "description": "",
        "creator": {"login": "", "name": ""},
        "contributors": [],
        "decisions": [],
        "queries": []
    }
    return collection

__all__ = ['git_actions',
           'helper',
           'validation',
           'collections_shard',
           'collections_umbrella']
from peyotl.collections.collections_umbrella import TreeCollectionStore, \
                                                    TreeCollectionStoreProxy, \
                                                    OWNER_ID_PATTERN, \
                                                    COLLECTION_ID_PATTERN
from peyotl.utility.input_output import read_as_json
from peyotl.utility.str_util import is_str_type

def collection_to_included_trees(collection):
    '''Takes a collection object (or a filepath to collection object), returns
    each element of the `decisions` list that has the decision set to included.
    '''
    if is_str_type(collection):
        collection = read_as_json(collection)
    inc = []
    for d in collection.get('decisions', []):
        if d['decision'] == 'INCLUDED':
            inc.append(d)
    return inc
