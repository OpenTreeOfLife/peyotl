#!/usr/bin/env python
from peyotl.api.wrapper import _WSWrapper, APIWrapper
import anyjson
from peyotl import get_logger
_LOG = get_logger(__name__)


class _OTIWrapper(_WSWrapper):
    '''Wrapper around OTI which is a text-searching index that wraps the findAllStudies
    stored in the phylesystem. You can search for studies, trees, or nodes.

    The find_nodes, find_trees, and find_studies queries will do one of the following:
        * raise an HTTPError (from requests),
        * raise a RuntimeError (if the server returns an error statement), or
        * return the matched_studies list for the query
    matched_studies is a list of dictionaries with:
         "ot:studyId" -> string for the matching study
         "matched_trees" -> list (if trees or nodes are the targets of the search).
    matched_trees is a list of dictionaries with:
        "nexson_id" -> string ID of the tree in the NexSON 
        "oti_tree_id" -> oti's internal ID for the tree (concatenation of study ID and tree ID)
        "matched_nodes" -> list
    matched_nodes is a list of dictionaries with:
        "nexson_id" -> string ID of the node within the tree

    Supports searching for nodes by:
        ot:age
        ot:ageMax
        ot:ageMin
        ot:comment
        ot:isIngroup
        ot:isLeaf
        ot:nodeLabel
        ot:originalLabel
        ot:ottId
        ot:ottTaxonName
        ot:parent
        ot:tag
        ot:treebaseOTUId

    wrapped methods:
        getSearchablePropertiesForStudies
        getSearchablePropertiesForTreeNodes
        getSearchablePropertiesForTrees

        singlePropertySearchForTreeNodes
        singlePropertySearchForStudies
        singlePropertySearchForTrees

        findAllStudies

    not wrapped:
        execute_query (dev only - not secure)
        execute_script (dev only - not secure)
        unindexNexsons (called by phylesystem-api)
        indexNexsons (called by phylesystem-api)
    '''
    def __init__(self, domain):
        self._node_search_prop = None
        self._tree_search_prop = None
        self._study_search_prop = None
        self.indexing_prefix = None
        self.query_prefix = None
        _WSWrapper.__init__(self, domain)
        self.set_domain(domain)
    def set_domain(self, d):
        self._node_search_prop = None
        self._tree_search_prop = None
        self._study_search_prop = None
        self._domain = d
        self.indexing_prefix = '{d}/ext/IndexServices/graphdb'.format(d=d)
        self.query_prefix = '{d}/ext/QueryServices/graphdb'.format(d=d)
    domain = property(_WSWrapper.get_domain, set_domain)
    def get_node_search_term_set(self):
        if self._node_search_prop is None:
            self._node_search_prop = set(self._do_node_searchable_properties_call())
        return self._node_search_prop
    node_search_term_set = property(get_node_search_term_set)
    def _do_node_searchable_properties_call(self):
        uri = '{p}/getSearchablePropertiesForTreeNodes'.format(p=self.query_prefix)
        return self._post(uri)
    def find_nodes(self, query_dict, exact=False, verbose=False):
        return self._do_query('{p}/singlePropertySearchForTreeNodes'.format(p=self.query_prefix),
                              query_dict=query_dict,
                              exact=exact,
                              verbose=verbose,
                              valid_keys=self.node_search_term_set)
    def _do_query(self, url, query_dict, exact, verbose, valid_keys):
        data = self._prepare_query_data(query_dict=query_dict,
                                        exact=exact,
                                        verbose=verbose,
                                        valid_keys=self.node_search_term_set)
        response = self._post(url, data=anyjson.dumps(data))
        if 'error' in response:
            raise RuntimeError('Error reported by oti "{}"'.format(response['error']))
        assert(len(response) == 1)
        return response['matched_studies']

    def _prepare_query_data(self, query_dict, exact, verbose, valid_keys):
        p, v = self._process_query_dict(query_dict, valid_keys)
        return {'property': p,
                'value': v,
                'exact': exact,
                'verbose': verbose}
        
    def _process_query_dict(self, query_dict, valid_keys):
        nq = len(query_dict)
        if nq != 1:
            if nq == 0:
                raise ValueError('The property/value pairs for the query should be passed in as keyword arguments')
            raise NotImplementedError('Currently only searches for one property/value pair are supported')
        k = query_dict.keys()[0]
        if k not in valid_keys:
            raise ValueError('"{k}" is not a valid search term. Expecting it to be one of the following: {kl}'.format(k=k, kl=repr(valid_keys)))
        v = query_dict[k]
        if not (isinstance(v, str) or isinstance(v, unicode)):
            v = unicode(v)
        return (k, v)
def OTI(domains=None):
    return APIWrapper(domains=domains).oti
