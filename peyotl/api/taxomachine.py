#!/usr/bin/env python
from peyotl.api.wrapper import _WSWrapper, APIWrapper
import anyjson
from peyotl import get_logger
_LOG = get_logger(__name__)

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
             do_approximate_matching=None):
        '''Takes a name and optional contextName returns a list of matches.
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
                if fuzzy_matching:
                    data['do_approximate_matching'] = True
                if id_list:
                    data['ids'] = list(id_list)
                if include_deprecated:
                    data['include_deprecated'] = True
                if include_dubious:
                    data['include_dubious'] = True
        return self.json_http_post(uri, data=anyjson.dumps(data))

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
    def __init__(self, domain):
        self.use_v1 = False
        self._contexts = None
        self._valid_contexts = None
        self.prefix = None
        _WSWrapper.__init__(self, domain)
        self.set_domain(domain)
    def set_domain(self, d):
        self._contexts = None
        self._valid_contexts = None
        self._domain = d
        if self.use_v1:
            self.prefix = '{d}/taxomachine/ext/TNRS/graphdb'.format(d=d)
        else:
            self.prefix = '{d}/v2/tnrs'.format(d=d)
            self.taxonomy_prefix = '{d}/v2/taxonomy'.format(d=d)
    domain = property(_WSWrapper.get_domain, set_domain)
    def info(self):
        if self.use_v1:
            raise NotImplementedError('"about" method not implemented')
        uri = '{p}/about'.format(p=self.taxonomy_prefix)
        return self.json_http_post(uri)
    about = info
    def taxon(self, ott_id, include_lineage=False):
        if self.use_v1:
            raise NotImplementedError('"taxon" method not implemented')
        data = {'ott_id': int(ott_id), 
                'include_lineage': bool(include_lineage)}
        uri = '{p}/taxon'.format(p=self.taxonomy_prefix)
        return self.json_http_post(uri, data=anyjson.dumps(data))
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
    def _get_valid_contexts(self):
        if self._valid_contexts is None:
            c = self.contexts()
            v = set()
            for cn in c.values():
                v.update(cn)
            self._valid_contexts = v
        return self._valid_contexts
    valid_contexts = property(_get_valid_contexts)

def Taxomachine(domains=None, **kwargs):
    return APIWrapper(domains=domains, **kwargs).taxomachine
