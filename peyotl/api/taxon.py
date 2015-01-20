#!/usr/bin/env python
'''This file contains a wrapper around a data structure representing
a taxon. We use "otu" because that is the term used in NeXML (and otNexSON).

'''
_EMPTY_TUPLE = tuple()

class TaxonWrapper(object):
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
            self._treemachine_node_id = prop_dict.get('treemachine_node_id')
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
    def parent(self):
        return self._parent
    @property
    def taxonomy(self):
        return self._taxonomy
    @property
    def taxomachine_wrapper(self):
        return self._taxomachine_wrapper
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
    def treemachine_node_id(self):
        return self._treemachine_node_id
    @property
    def rank(self):
        return self._rank
    @property
    def unique_name(self):
        return self._unique_name
    @property
    def nomenclature_code(self):
        return self._nomenclature_code

    def write_report(self, output):
        if self.taxomachine_wrapper:
            output.write('Taxon info query was obtained from: {} \n'.format(self.taxomachine_wrapper.endpoint))
        if self.taxonomy:
            output.write('The taxonomic source is\n')
            output.write(' {}'.format(self.taxonomy.source))
            output.write(' by {}\n'.format(self.taxonomy.author))
            output.write('Information for the taxonomy can be found at {}\n'.format(self.taxonomy.weburl))
        output.write('OTT ID (ot:ottId) = {}\n'.format(self.ott_id))
        output.write('    name (ot:ottTaxonName) = "{}"\n'.format(self.name))
        output.write('    is a junior synonym ? {}\n'.format(bool(self.is_synonym)))
        if self.is_deprecated is not None:
            output.write('    is deprecated from OTT? {}\n'.format(self.is_deprecated))
        if self.is_dubious is not None:
            output.write('    is dubious taxon? {}\n'.format(self.is_dubious))
        if self.synonyms:
            output.write('    known synonyms: "{}"\n'.format('", "'.join(self.synonyms)))
        if self.flags:
            output.write('    OTT flags for this taxon: {}\n'.format(self.flags))
        if self.rank:
            output.write('    The taxonomic rank associated with this name is: {}\n'.format(self.rank))
        if self.nomenclature_code:
            output.write('    The nomenclatural code for this name is: {}\n'.format(self.nomenclature_code))
        if self.taxomachine_node_id:
            f = '    The (unstable) node ID in the current taxomachine instance is: {}\n'
            f = f.format(self.taxomachine_node_id)
            output.write(f)
        if self.treemachine_node_id:
            f = '    The (unstable) node ID in the current treemachine instance is: {}\n'
            f = f.format(self.treemachine_node_id)
            output.write(f)

