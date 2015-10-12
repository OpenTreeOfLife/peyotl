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
import copy

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

def concatenate_collections(collection_list):
    r = get_empty_collection()
    r_decisions = r['decisions']
    r_contributors = r['contributors']
    r_queries = r['queries']
    contrib_set = set()
    inc_set = set()
    not_inc_set = set()
    for n, coll in enumerate(collection_list):
        r_queries.extend(coll['queries'])
        for contrib in coll['contributors']:
            l = contrib['login']
            if l not in contrib_set:
                r_contributors.append(contrib)
                contrib_set.add(l)
        for d in coll['decisions']:
            key = '{}_{}'.format(d['studyID'], d['treeID'])
            inc_d = d['decision'].upper() == 'INCLUDED'
            if key in inc_set:
                if not inc_d:
                    raise ValueError('Collections disagree on inclusion of study_tree = "{}"'.format(key))
            elif key in not_inc_set:
                if inc_d:
                    raise ValueError('Collections disagree on inclusion of study_tree = "{}"'.format(key))
            else:
                if inc_d:
                    inc_set.add(key)
                else:
                    not_inc_set.add(key)
                r_decisions.append(d)
    return r
