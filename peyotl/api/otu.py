#!/usr/bin/env python
'''This file contains a wrapper around a data structure representing
a taxon. We use "otu" because that is the term used in NeXML (and otNexSON).

'''
_EMPTY_TUPLE = tuple()

class OTUWrapper(object):
    def __init__(self, taxomachine_wrapper=None, taxonomy=None, prop_dict=None, ott_id=None):
        '''prop_dict can be the dict for a taxon from a OToL API call
        '''
        if prop_dict is None:
            self._ott_id = ott_id
        else:
            if ott_id is None:
                self._ott_id = prop_dict['ot:ottId']
            else:
                self._ott_id = ott_id
            self._is_deprecated = prop_dict.get('is_deprecated')
            self._is_dubious = prop_dict.get('is_dubious')
            self._is_synonym = prop_dict.get('is_synonym')
            self._flags = prop_dict.get('flags')
            if self._flags is None:
                self._flags = _EMPTY_TUPLE #TODO should convert to frozenset
            self._synonyms = prop_dict.get('synonyms')
            if self._synonyms is None:
                self._synonyms = _EMPTY_TUPLE
            self._taxomachine_node_id = prop_dict.get('matched_node_id')
            if self._taxomachine_node_id is None:
                self._taxomachine_node_id = prop_dict.get('node_id')
            self._rank = prop_dict.get('rank')
            self._unique_name = prop_dict.get('unique_name')
            self._nomenclature_code = prop_dict.get('nomenclature_code')
            self._ott_taxon_name = prop_dict.get('ot:ottTaxonName')
            self._taxonomy = taxonomy
            self._taxomachine_wrapper = taxomachine_wrapper
            self._taxonomic_lineage = prop_dict.get('taxonomic_lineage')
            self._parent = prop_dict.get('parent')
            if self._parent is None and self._taxomachine_wrapper is not None and self._taxonomic_lineage:
                self._fill_parent_attr()
    def _fill_parent_attr(self):
        self._parent = self._taxomachine_wrapper.get_cached_parent_for_taxon(self)

    def update_empty_fields(self, **kwargs):
        '''Updates the field of info about an OTU that might not be filled in by a match_names or taxon call.'''
        if self._is_deprecated is None:
            self._is_deprecated = kwargs.get('is_deprecated')
        if self._is_dubious is None:
            self._is_dubious = kwargs.get('is_dubious')
        if self._is_synonym is None:
            self._is_synonym = kwargs.get('is_synonym')
        if self._synonyms is _EMPTY_TUPLE:
            self._synonyms = kwargs.get('synonyms')
            if self._synonyms is None:
                self._synonyms = _EMPTY_TUPLE
        if self.rank is None:
            self._rank = kwargs.get('rank')
        if self._nomenclature_code:
            self._nomenclature_code = kwargs.get('nomenclature_code')
        if not self._unique_name:
            self._unique_name = kwargs.get('unique_name')
        if self._taxonomic_lineage is None:
            self._taxonomic_lineage = kwargs.get('taxonomic_lineage')
        if self._parent is None:
            self._parent = kwargs.get('parent')
            if self._parent is None and self._taxomachine_wrapper is not None and self._taxonomic_lineage:
                self._fill_parent_attr()
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
