#!/usr/bin/env python
from peyotl.utility.dict_wrapper import FrozenDictAttrWrapper, FrozenDictWrapper
from peyotl.api.taxon import TaxonWrapper, TaxonHolder
from peyotl.utility import get_config_object, get_logger
from peyotl.api.wrapper import _WSWrapper, APIWrapper
import weakref
import anyjson
_LOG = get_logger(__name__)
_EMPTY_TUPLE = tuple()
class TaxonomyInfoWrapper(FrozenDictAttrWrapper):
    pass

class TNRSMatch(TaxonHolder):
    '''Delegates to an TaxonWrapper object and adds score and is_approximate_match properties.
    part of a "wrapped" TNRS (or match_names) response.
    '''
    def __init__(self, prop_dict, taxomachine_wrapper=None, taxonomy=None, taxon=None):
        if taxon is None:
            taxon = TaxonWrapper(taxomachine_wrapper=taxomachine_wrapper,
                                 taxonomy=taxonomy,
                                 prop_dict=prop_dict)
        TaxonHolder.__init__(self, taxon)
        self._score = prop_dict.get('score')
        self._is_approximate_match = prop_dict.get('is_approximate_match')
    @property
    def ott_taxon_name(self):
        return self._taxon.ott_taxon_name
    @property
    def score(self):
        return self._score
    @property
    def is_approximate_match(self):
        return self._is_approximate_match

class TNRSResponse(FrozenDictWrapper):
    '''The class for return value of of TNRS and match_names calls if wrap_response is True
    This provides . access to the top-level properties returned by the TNRS, but also
    adds dict-like behavior where the searched names are the keys, to make it easier
        to access the tuple of matched names for each searched name. The elements in each
        tuple will be TNRSMatch objects. Unmatched names will map to an empty tuple.
    the `taxonomy` field will be a TaxonomyInfoWrapper object
    '''
    def __init__(self, taxomachine_wrapper, response, query_data):
        tw = taxomachine_wrapper
        m = {}
        taxonomy = TaxonomyInfoWrapper(response['taxonomy'])
        for o in response['results']:
            if tw:
                m[o['id']] = tuple([tw.get_tnrs_match_from_response(i, taxonomy) for i in o['matches']])
            else:
                m[o['id']] = tuple([TNRSMatch(i, taxonomy=taxonomy, taxomachine_wrapper=None) for i in o['matches']])
        for name in response['unmatched_name_ids']:
            m[name] = _EMPTY_TUPLE
        FrozenDictWrapper.__init__(self, m)
        object.__setattr__(self, '_query_data', query_data)
        object.__setattr__(self, '_raw_response', response)
        object.__setattr__(self, 'taxonomy', taxonomy)
        object.__setattr__(self, 'governing_code', response['governing_code'])
        object.__setattr__(self, 'unambiguous_name_ids', response['unambiguous_name_ids'])
        object.__setattr__(self, 'unmatched_name_ids', response['unmatched_name_ids'])
        object.__setattr__(self, 'matched_name_ids', response['matched_name_ids'])
        object.__setattr__(self, 'context', response['context'])
        object.__setattr__(self, 'includes_deprecated_taxa', response['includes_deprecated_taxa'])
        object.__setattr__(self, 'includes_dubious_names', response['includes_dubious_names'])
        object.__setattr__(self, 'includes_approximate_matches', response['includes_approximate_matches'])
    @property
    def raw_response(self):
        return self._raw_response #pylint: disable=E1101
    @property
    def context_inferred(self):
        return self._query_data.get('context_name') is None #pylint: disable=E1101
    @property
    def matched_names(self):
        return [k for k, v in self._raw_dict.items() if v is not _EMPTY_TUPLE] #pylint: disable=E1101

class _TaxomachineAPIWrapper(_WSWrapper):
    '''Wrapper around interactions with the taxomachine TNRS.
    The primary service is TNRS (for taxonomic name resolution service)
        which takes a name matches it to OTT
    In this wrapper implementation, he naming contexts are cached in:
        _contexts as the raw return (dictionary of large group name
            to context name within that group), and
        _valid_contexts a set of all context names.
    For example in May of 2014, the contexts are:
        {
        'PLANTS': ['Land plants',
                   'Hornworts',
                   'Mosses',
                   'Liverworts',
                   'Vascular plants',
                   'Club mosses',
                   'Ferns',
                   'Seed plants',
                   'Flowering plants',
                   'Monocots',
                   'Eudicots',
                   'Asterids',
                   'Rosids'],
        'LIFE': ['All life'],
        'ANIMALS': ['Animals',
                    'Birds',
                    'Tetrapods',
                    'Mammals',
                    'Amphibians',
                    'Vertebrates',
                    'Arthropods',
                    'Molluscs',
                    'Platyhelminthes',
                    'Annelids',
                    'Cnidarians',
                    'Arachnides',
                    'Insects'],
        'BACTERIA': ['Bacteria'],
        'FUNGI': ['Fungi']
        }

    https://github.com/OpenTreeOfLife/opentree/blob/master/neo4j_services_docs.md

    NOTES:
        Do we need a get_OTT_version method in taxomachine?
        contextQueryForNames args are confusing
        do we want an "includeDubious" for autocompleteBoxQuery ?
        What is the use case for getContextForNames
        Is there a use case for getNodeIDJSONFromName if we don't support CQL?
        Is there any significance to the order of return for autocompleteBoxQuery ?
        is the "name" in the autocompleteBoxQuery return the uniqname from OTT or name?
    OTT wrapper to add:
        synonym finder ?
        parent taxon ?
        homonym finder ?
    '''
    def TNRS(self,
             names,
             context_name=None,
             id_list=None,
             fuzzy_matching=False,
             include_deprecated=False,
             include_dubious=False,
             do_approximate_matching=None,
             wrap_response=None):
        '''Takes a name and optional contextName returns a list of matches.
        `wrap_response` can be True to return a TNRSResponse object, None to return
            the "raw" response dict, or a function/class that takes (response, query_data=dict)
            as its arguments.

        Each match is a dict with:
           'higher' boolean DEF???
           'exact' boolean for exact match
           'ottId' int
           'name'  name (or uniqname???) for the taxon in OTT
           'nodeId' int ID of not in the taxomachine db. probably not of use to anyone...
        '''
        #if context_name is None:
        #    context_name = 'All life'
        if do_approximate_matching is not None:
            fuzzy_matching = do_approximate_matching
        if context_name and context_name not in self.valid_contexts:
            raise ValueError('"{}" is not a valid context name'.format(context_name))
        if not (isinstance(names, list) or isinstance(names, tuple)):
            names = [names]
        for name in names:
            if len(name) < 2:
                raise ValueError('Name "{}" found. Names must have at least 2 characters!'.format(name))
        if id_list and len(id_list) != len(names):
            raise ValueError('"id_list must be the same size as "names"')
        data = {'names': names}
        if self.use_v1:
            uri = '{p}/contextQueryForNames'.format(p=self.prefix)
        else:
            uri = '{p}/match_names'.format(p=self.prefix)
        if context_name:
            if self.use_v1:
                data['contextName'] = context_name
            else:
                data['context_name'] = context_name
        data['do_approximate_matching'] = bool(fuzzy_matching)
        if id_list:
            data['ids'] = list(id_list)
        if include_deprecated:
            data['include_deprecated'] = True
        if include_dubious:
            data['include_dubious'] = True
        resp = self.json_http_post(uri, data=anyjson.dumps(data))
        if wrap_response is None or wrap_response is False:
            return resp
        if wrap_response is True:
            return TNRSResponse(self._wr, resp, query_data=data)
        return wrap_response(resp, query_data=data)

    def autocomplete(self, name, context_name=None, include_dubious=False):
        '''Takes a name and optional context_name returns a list of matches.
        Each match is a dict with:
           'higher' boolean DEF???
           'exact' boolean for exact match
           'ottId' int
           'name'  name (or uniqname???) for the taxon in OTT
           'nodeId' int ID of not in the taxomachine db. probably not of use to anyone...
        '''
        if context_name and context_name not in self.valid_contexts:
            raise ValueError('"{}" is not a valid context name'.format(context_name))
        if self.use_v1:
            uri = '{p}/autocompleteBoxQuery'.format(p=self.prefix)
            data = {'queryString': name}
            if context_name:
                data['contextName'] = context_name
        else:
            uri = '{p}/autocomplete_name'.format(p=self.prefix)
            data = {'name': name}
            if context_name:
                data['context_name'] = context_name
            if include_dubious:
                data['include_dubious'] = True
        return self.json_http_post(uri, data=anyjson.dumps(data))
    def infer_context(self, names):
        if self.use_v1:
            raise NotImplementedError("infer_context not wrapped in v1")
        uri = '{p}/infer_context'.format(p=self.prefix)
        data = {'names': names}
        return self.json_http_post(uri, data=anyjson.dumps(data))
    def __init__(self, domain, **kwargs):
        self._config = kwargs.get('config')
        if self._config is None:
            self._config = get_config_object()
        self._api_vers = self._config.get_from_config_setting_cascade([('apis', 'taxomachine_api_version'),
                                                                       ('apis', 'api_version')],
                                                                      "2")
        self.use_v1 = (self._api_vers == "1")
        r = self._config.get_from_config_setting_cascade([('apis', 'taxomachine_raw_urls'),
                                                          ('apis', 'raw_urls')],
                                                         "FALSE")
        self._raw_urls = (r.lower() == 'true')
        if 'cache_taxa' in kwargs:
            cache_taxa = kwargs.get('cache_taxa', False)
        else:
            cache_taxa = self._config.get_config_setting('apis', 'cache_taxa', 'false').lower() in ['true', '1']
        if cache_taxa:
            self._ott_id2taxon = {}
        else:
            self._ott_id2taxon = None
        self._contexts = None
        self._valid_contexts = None
        self.prefix = None
        _WSWrapper.__init__(self, domain, **kwargs)
        self.domain = domain
        self._wr = weakref.proxy(self)
    @property
    def domain(self):
        return self._domain
    @domain.setter
    def domain(self, d):#pylint: disable=W0221
        self._contexts = None
        self._valid_contexts = None
        self._domain = d
        if self._raw_urls:
            self.prefix = '{d}/taxomachine/ext/TNRS/graphdb'.format(d=d)
        elif self.use_v1:
            self.prefix = '{d}/taxomachine/v1'.format(d=d)
        else:
            self.prefix = '{d}/v2/tnrs'.format(d=d)
            self.taxonomy_prefix = '{d}/v2/taxonomy'.format(d=d)
    def info(self):
        if self.use_v1:
            raise NotImplementedError('"about" method not implemented')
        uri = '{p}/about'.format(p=self.taxonomy_prefix)
        return self.json_http_post(uri)
    about = info
    def taxon(self, ott_id, include_lineage=False, list_terminal_descendants=False, wrap_response=None):
        if self.use_v1:
            raise NotImplementedError('"taxon" method not implemented')
        data = {'ott_id': int(ott_id),
                'include_lineage': bool(include_lineage),
                'list_terminal_descendants': bool(list_terminal_descendants)}
        uri = '{p}/taxon'.format(p=self.taxonomy_prefix)
        r = self.json_http_post(uri, data=anyjson.dumps(data))
        if 'error' in r:
            raise ValueError(r['error'])
        if wrap_response:
            #TODO we should fetch info about the taxanomy, so that we can
            #   provide a taxonomy kwarg to TaxonWrapper...
            return TaxonWrapper(taxomachine_wrapper=self._wr, prop_dict=r)
        return r
    def subtree(self, ott_id):
        if self.use_v1:
            raise NotImplementedError('"subtree" method not implemented')
        data = {'ott_id': int(ott_id), }
        uri = '{p}/subtree'.format(p=self.taxonomy_prefix)
        return self.json_http_post(uri, data=anyjson.dumps(data))
    def lica(self, ott_ids, include_lineage=False):
        if self.use_v1:
            raise NotImplementedError('"lica" method not implemented')
        data = {'ott_ids': [int(i) for i in ott_ids],
                'include_lineage': bool(include_lineage)}
        uri = '{p}/lica'.format(p=self.taxonomy_prefix)
        return self.json_http_post(uri, data=anyjson.dumps(data))
    def contexts(self):
        # Taxonomic name contexts. These are cached in _contexts
        if self._contexts is None:
            self._contexts = self._do_contexts_call()
        return self._contexts
    def _do_contexts_call(self):
        if self.use_v1:
            uri = '{p}/getContextsJSON'.format(p=self.prefix)
        else:
            uri = '{p}/contexts'.format(p=self.prefix)
        return self.json_http_post(uri)
    @property
    def valid_contexts(self):
        if self._valid_contexts is None:
            c = self.contexts()
            v = set()
            for cn in c.values():
                v.update(cn)
            self._valid_contexts = v
        return self._valid_contexts

    def names_to_ott_ids_perfect(self, names, **kwargs):
        '''delegates a call to TNRS (same arguments as that function).

        Returns a list of (non-dubious) OTT IDs in the same order as the original names.
        Raises a ValueError if each name does not have exactly one perfect, non-dubious
        (score = 1.0) match in the TNRS results.
        '''
        results = self.TNRS(names, **kwargs)['results']
        d = {}
        for blob in results:
            query_name = blob["id"]
            m = blob["matches"]
            perf_ind = None
            for i, poss_m in enumerate(m):
                if (not poss_m['is_approximate_match']) and (not poss_m['is_dubious']):
                    if perf_ind is None:
                        perf_ind = i
                    else:
                        raise ValueError('Multiple matches for "{q}"'.format(q=query_name))
            if perf_ind is None:
                raise ValueError('No matches for "{q}"'.format(q=query_name))
            d[query_name] = m[perf_ind]['ot:ottId']
        ret = []
        for query_name in names:
            ni = d.get(query_name)
            if ni is None:
                raise ValueError('No matches for "{q}"'.format(q=query_name))
            ret.append(ni)
        return ret
    def get_cached_parent_for_taxon(self, child_taxon):
        '''If the taxa are being cached, this call will create a the lineage "spike" for taxon child_taxon

        Expecting child_taxon to have a non-empty _taxonomic_lineage with response dicts that can create
            an ancestral TaxonWrapper.
        '''
        if self._ott_id2taxon is None:
            resp = child_taxon._taxonomic_lineage[0]
            tl = child_taxon._taxonomic_lineage[1:]
            assert 'taxonomic_lineage' not in resp
            resp['taxonomic_lineage'] = tl
            return TaxonWrapper(taxonomy=child_taxon.taxonomy,
                                taxomachine_wrapper=self._wr,
                                prop_dict=resp) #TODO recursive (indirectly)
        else:
            anc = []
            prev = None
            for resp in reversed(child_taxon._taxonomic_lineage):
                ott_id = resp['ot:ottId']
                curr = self._ott_id2taxon.get(ott_id)
                if curr is None:
                    assert 'taxonomic_lineage' not in resp
                    assert 'parent' not in resp
                    resp['parent'] = prev
                    resp['taxonomic_lineage'] = anc
                    curr = TaxonWrapper(taxonomy=child_taxon.taxonomy,
                                        taxomachine_wrapper=self._wr,
                                        prop_dict=resp)
                elif curr._parent is None and prev is not None:
                    curr._parent = prev
                prev = curr
                anc.insert(0, curr)
            return prev


    def get_tnrs_match_from_response(self, resp, taxonomy):
        if self._ott_id2taxon is None:
            return TNRSMatch(resp, taxonomy=taxonomy, taxomachine_wrapper=self._wr)
        ott_id = resp['ot:ottId']
        taxon = self._ott_id2taxon.get(ott_id)
        if taxon is None:
            tnrsm = TNRSMatch(resp, taxonomy=taxonomy, taxomachine_wrapper=self._wr)
            self._ott_id2taxon[ott_id] = tnrsm._taxon
            return tnrsm
        return TNRSMatch(resp, taxonomy=taxonomy, taxomachine_wrapper=self._wr, taxon=taxon)
def Taxomachine(domains=None, **kwargs):
    return APIWrapper(domains=domains, **kwargs).taxomachine
