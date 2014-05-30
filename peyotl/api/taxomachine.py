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
    def TNRS(self, name, contextName=None):
        '''Takes a name and optional contextName returns a list of matches.
        Each match is a dict with:
           'higher' boolean DEF???
           'exact' boolean for exact match
           'ottId' int
           'name'  name (or uniqname???) for the taxon in OTT
           'nodeId' int ID of not in the taxomachine db. probably not of use to anyone...
        '''
        if contextName and contextName not in self.valid_contexts:
            raise ValueError('"{}" is not a valid context name'.format(contextName))
        uri = '{p}/autocompleteBoxQuery'.format(p=self.prefix)
        data = {'queryString': name}
        if contextName:
            data['contextName'] = contextName
        return self.json_http_post(uri, data=anyjson.dumps(data))
    def __init__(self, domain):
        self._contexts = None
        self._valid_contexts = None
        self.prefix = None
        _WSWrapper.__init__(self, domain)
        self.set_domain(domain)
    def set_domain(self, d):
        self._contexts = None
        self._valid_contexts = None
        self._domain = d
        self.prefix = '{d}/taxomachine/ext/TNRS/graphdb'.format(d=d)
    domain = property(_WSWrapper.get_domain, set_domain)
    def contexts(self):
        # Taxonomic name contexts. These are cached in _contexts
        if self._contexts is None:
            self._contexts = self._do_contexts_call()
        return self._contexts
    def _do_contexts_call(self):
        uri = '{p}/getContextsJSON'.format(p=self.prefix)
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

def Taxomachine(domains=None):
    return APIWrapper(domains=domains).taxomachine
