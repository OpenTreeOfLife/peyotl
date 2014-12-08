#!/usr/bin/env python
'''This file contains a wrapper around a data structure representing
a taxon. We use "otu" because that is the term used in NeXML (and otNexSON).

'''
_EMPTY_TUPLE = tuple()

class OTUWrapper(object):
    def __init__(self, taxomachine_wrapper=None, taxonomy=None, **kwargs):
        '''kwargs can be the dict for a taxon from a OToL API call
        '''
        self._is_deprecated = kwargs.get('is_deprecated')
        self._is_dubious = kwargs.get('is_dubious')
        self._is_synonym = kwargs.get('is_synonym')
        self._flags = kwargs.get('flags')
        if self._flags is None:
            self._flags = _EMPTY_TUPLE #TODO should convert to frozenset
        self._synonyms = kwargs.get('synonyms')
        if self._synonyms is None:
            self._synonyms = _EMPTY_TUPLE
        self._ott_id = kwargs.get('ot:ottId')
        self._taxomachine_node_id = kwargs.get('matched_node_id')
        if self._taxomachine_node_id is None:
            self._taxomachine_node_id = kwargs.get('node_id')
        self._rank = kwargs.get('rank')
        self._unique_name = kwargs.get('unique_name')
        self._nomenclature_code = kwargs.get('nomenclature_code')
        self._ott_taxon_name = kwargs.get('ot:ottTaxonName')
        self._taxonomy = taxonomy
        self._taxomachine_wrapper = taxomachine_wrapper
    @property
    def ott_taxon_name(self):
        return self._ott_taxon_name
    @property
    def name(self):
        return self._ott_taxon_name
    @property
    def is_deprecated(self):
        return self._is_deprecated
    @property
    def is_dubious(self):
        return self._is_dubious

    @property
    def is_synonym(self):
        return self._is_synonym
    @property
    def flags(self):
        return self._flags
    @property
    def synonyms(self):
        return self._synonyms
    @property
    def ott_id(self):
        return self._ott_id
    @property
    def taxomachine_node_id(self):
        return self._taxomachine_node_id
    @property
    def rank(self):
        return self._rank
    @property
    def unique_name(self):
        return self._unique_name
    @property
    def nomenclature_code(self):
        return self._nomenclature_code
