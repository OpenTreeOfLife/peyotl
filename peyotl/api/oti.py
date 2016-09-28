#!/usr/bin/env python
from peyotl.utility.str_util import UNICODE, is_str_type, underscored2camel_case
from peyotl.api.wrapper import _WSWrapper, APIWrapper
from peyotl.api.study_ref import TreeRefList
from peyotl.nexson_syntax import create_content_spec
from peyotl.utility import doi2url, get_config_object, get_logger
import anyjson
_LOG = get_logger(__name__)
_OTI_NEXSON_SCHEMA = create_content_spec(format='nexson', nexson_version='0.0.0')


class _OTIWrapper(_WSWrapper):
    '''Wrapper around OTI which is a text-searching index that wraps the findAllStudies
    stored in the phylesystem. You can search for studies, trees, or nodes.

    The primary attributes of interest are:
        node_search_term_set,
        study_search_term_set, and
        tree_search_term_set
    The primary methods of interest are:
        find_all_studies,
        find_nodes,
        find_studies, and
        find_trees

    The find_nodes, find_trees, and find_studies queries will do one of the following:
        * raise an HTTPError (from requests),
        * raise a RuntimeError (if the server returns an error statement), or
        * return the matched_studies list for the query
    search terms can be sent in as keys+values in a dict or using a keyword arguments
        The key in the keyword arg will have "ot:" prepended to it, if it is not
        an already valid search term.

    matched_studies is a list of dictionaries with:
         "ot:studyId" -> string for the matching study
         "matched_trees" -> list (if trees or nodes are the targets of the search).
    matched_trees is a list of dictionaries with:
        "nexson_id" -> string ID of the tree in the NexSON
        "oti_tree_id" -> oti's internal ID for the tree (concatenation of study ID and tree ID)
        "matched_nodes" -> list
    matched_nodes is a list of dictionaries with:
        "nexson_id" -> string ID of the node within the tree

    As of May 30, 2014:
    Nodes can be searched for using:
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

    Trees can be searched for using:
        is_deprecated
        ot:branchLengthDescription
        ot:branchLengthMode
        ot:branchLengthTimeUnits
        ot:comment
        ot:inferenceMethod
        ot:nodeLabelDescription
        ot:nodeLabelMode
        ot:originalLabel
        ot:ottId
        ot:ottTaxonName
        ot:studyId
        ot:tag
        ot:treeLastEdited
        ot:treeModified
        ot:treebaseOTUId
        ot:treebaseTreeId
        oti_tree_id

    Studies can be searched for using:
        is_deprecated
        ot:authorContributed
        ot:comment
        ot:curatorName
        ot:dataDeposit
        ot:focalClade
        ot:focalCladeOTTId
        ot:focalCladeOTTTaxonName
        ot:focalCladeTaxonName
        ot:studyId
        ot:studyLabel
        ot:studyLastEditor
        ot:studyModified
        ot:studyPublication
        ot:studyPublicationReference
        ot:studyUploaded
        ot:studyYear
        ot:tag

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

    def find_nodes(self, query_dict=None, exact=False, verbose=False, **kwargs):
        '''Query on node properties. See documentation for _OTIWrapper class.'''
        assert self.use_v1
        return self._do_query('{p}/singlePropertySearchForTreeNodes'.format(p=self.query_prefix),
                              query_dict=query_dict,
                              exact=exact,
                              verbose=verbose,
                              valid_keys=self.node_search_term_set,
                              kwargs=kwargs)
    def find_trees(self, query_dict=None, exact=False, verbose=False, wrap_response=False, **kwargs):
        '''Query on tree properties. See documentation for _OTIWrapper class.'''
        if self.use_v1:
            uri = '{p}/singlePropertySearchForTrees'.format(p=self.query_prefix)
        else:
            uri = '{p}/find_trees'.format(p=self.query_prefix)
        resp = self._do_query(uri,
                              query_dict=query_dict,
                              exact=exact,
                              verbose=verbose,
                              valid_keys=self.tree_search_term_set,
                              kwargs=kwargs)
        if wrap_response:
            return TreeRefList(resp)
        return resp
    def find_studies(self, query_dict=None, exact=False, verbose=False, **kwargs):
        '''Query on study properties. See documentation for _OTIWrapper class.'''
        if self.use_v1:
            uri = '{p}/singlePropertySearchForStudies'.format(p=self.query_prefix)
        else:
            uri = '{p}/find_studies'.format(p=self.query_prefix)
        return self._do_query(uri,
                              query_dict=query_dict,
                              exact=exact,
                              verbose=verbose,
                              valid_keys=self.study_search_term_set,
                              kwargs=kwargs)
    def find_all_studies(self, include_trees=False, verbose=False):
        '''Returns  a list of dicts for the entire set of studies indexed by oti.
        If verbose and include_trees are False, each dict will just have the ot:studyId
        If verbose is True, then the keys could also include:
            ot:curatorName
            ot:dataDeposit
            ot:focalClade
            ot:focalCladeOTTTaxonName
            ot:studyPublication
            ot:studyPublicationReference
            ot:studyYear
            ot:tag
        If include_trees is True, then a matched_trees list may be contained in each
            dict.
        '''
        if not self.use_v1:
            return self.find_studies(verbose=verbose)
        url = '{p}/findAllStudies'.format(p=self.query_prefix)
        data = {'includeTreeMetadata': include_trees,
                'verbose': verbose,}
        response = self.json_http_post(url, data=anyjson.dumps(data))
        return response
    def __init__(self, domain, **kwargs):
        self._config = kwargs.get('config')
        if self._config is None:
            self._config = get_config_object()
        self._api_vers = self._config.get_from_config_setting_cascade([('apis', 'oti_api_version'),
                                                                       ('apis', 'api_version')],
                                                                      "2")
        self.use_v1 = (self._api_vers == "1")
        self._node_search_prop = None
        self._search_terms = None
        self._tree_search_prop = None
        self._study_search_prop = None
        self.indexing_prefix = None
        self.query_prefix = None
        r = self._config.get_from_config_setting_cascade([('apis', 'oti_raw_urls'),
                                                          ('apis', 'raw_urls')],
                                                         "FALSE")
        self._raw_urls = (r.lower() == 'true')
        _WSWrapper.__init__(self, domain, **kwargs)
        self.domain = domain
    @property
    def domain(self):
        return self._domain
    @domain.setter
    def domain(self, d): #pylint: disable=W0221
        self._node_search_prop = None
        self._search_terms = None
        self._tree_search_prop = None
        self._study_search_prop = None
        self._domain = d
        if self._raw_urls:
            self.indexing_prefix = '{d}/oti/ext/IndexServices/graphdb'.format(d=d)
            self.query_prefix = '{d}/oti/ext/QueryServices/graphdb'.format(d=d)
        else:
            if self.use_v1:
                self.indexing_prefix = '{d}/oti/IndexServices/graphdb'.format(d=d)
                self.query_prefix = '{d}/oti/QueryServices/graphdb'.format(d=d)
            else:
                self.indexing_prefix = '{d}/oti/IndexServices/graphdb'.format(d=d)
                self.query_prefix = '{d}/v2/studies'.format(d=d)
    @property
    def node_search_term_set(self):
        if self._node_search_prop is None:
            self._node_search_prop = set(self._do_node_searchable_properties_call())
        return self._node_search_prop
    def _do_searchable_properties_call(self):
        if self.use_v1:
            raise NotImplementedError('properties call added in v2')
        uri = '{p}/properties'.format(p=self.query_prefix)
        return self.json_http_post(uri)
    @property
    def search_terms(self):
        if self._search_terms is None:
            self._search_terms = {}
            d = self._do_searchable_properties_call()
            for k, v in d.items():
                self._search_terms[k] = frozenset(v)
        return dict(self._search_terms)
    def _do_tree_searchable_properties_call(self):
        if not self.use_v1:
            return self.search_terms['tree_properties']
        uri = '{p}/getSearchablePropertiesForTrees'.format(p=self.query_prefix)
        return self.json_http_post(uri)
    @property
    def tree_search_term_set(self):
        if self._tree_search_prop is None:
            self._tree_search_prop = set(self._do_tree_searchable_properties_call())
        return self._tree_search_prop
    def _do_study_searchable_properties_call(self):
        if not self.use_v1:
            return self.search_terms['study_properties']
        uri = '{p}/getSearchablePropertiesForStudies'.format(p=self.query_prefix)
        return self.json_http_post(uri)
    @property
    def study_search_term_set(self):
        if self._study_search_prop is None:
            self._study_search_prop = set(self._do_study_searchable_properties_call())
        return self._study_search_prop
    def _do_node_searchable_properties_call(self):
        if not self.use_v1:
            return self._do_searchable_properties_call().get('tree_properties', [])
        uri = '{p}/getSearchablePropertiesForTreeNodes'.format(p=self.query_prefix)
        return self.json_http_post(uri)
    def _do_query(self, url, query_dict, exact, verbose, valid_keys, kwargs):
        data = self._prepare_query_data(query_dict=query_dict,
                                        exact=exact,
                                        verbose=verbose,
                                        valid_keys=valid_keys,
                                        kwargs=kwargs)
        response = self.json_http_post(url, data=anyjson.dumps(data))
        if 'error' in response:
            raise RuntimeError('Error reported by oti "{}"'.format(response['error']))
        assert len(response) == 1
        return response['matched_studies']

    def _prepare_query_data(self, query_dict, exact, verbose, valid_keys, kwargs):
        r = self._process_query_dict(query_dict, valid_keys, kwargs)
        data = {'exact': exact,
                'verbose': verbose}
        if r:
            data['property'] = r[0]
            data['value'] = r[1]
        return data
    def _process_query_dict(self, query_dict, valid_keys, kwargs):
        if query_dict is None:
            query_dict = {}
        for k, v in kwargs.items():
            if k in valid_keys:
                query_dict[k] = v
            else:
                prefixed = 'ot:' + k
                if prefixed in valid_keys:
                    query_dict[prefixed] = v
                elif '_' in k:
                    cc = underscored2camel_case(k)
                    if cc in valid_keys:
                        query_dict[cc] = v
                    else:
                        prefixed_cc = 'ot:' + cc
                        if prefixed_cc in valid_keys:
                            query_dict[prefixed_cc] = v
                        else:
                            query_dict[k] = v
        nq = len(query_dict)
        if nq == 0:
            if self.use_v1:
                raise ValueError('The property/value pairs for the query should be passed in as keyword arguments')
            return None
        if nq > 1:
            raise NotImplementedError('Currently only searches for one property/value pair are supported')
        k = list(query_dict.keys())[0]
        if k not in valid_keys:
            m = '"{k}" is not a valid search term. Expecting it to be one of the following: {kl}'
            m = m.format(k=k, kl=repr(valid_keys))
            raise ValueError(m)
        v = query_dict[k]
        if not is_str_type(v):
            v = UNICODE(v)
        if k == 'ot:studyPublication':
            v = doi2url(v)
        return (k, v)
    def trigger_index(self, phylesystem_api, study_id):
        url = '{p}/indexNexsons'.format(p=self.indexing_prefix)
        nexson_url = phylesystem_api.url_for_api_get_study(study_id, schema=_OTI_NEXSON_SCHEMA)
        data = {'urls': [nexson_url]}
        return self.json_http_post(url, data=anyjson.dumps(data))
    def trigger_unindex(self, study_id):
        url = '{p}/unindexNexsons'.format(p=self.indexing_prefix)
        if is_str_type(study_id):
            study_id = [study_id]
        data = {'ids': study_id}
        return self.json_http_post(url, data=anyjson.dumps(data))
def OTI(domains=None, **kwargs):
    return APIWrapper(domains=domains, **kwargs).oti
