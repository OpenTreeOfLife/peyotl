#!/usr/bin/env python
'Badgerfish2DirectNexson class'
from peyotl.nexson_syntax.helper import NexsonConverter, \
                                        get_nexml_el, \
                                        _add_value_to_dict_bf, \
                                        _coerce_literal_val_to_primitive, \
                                        _cull_redundant_about, \
                                        _get_index_list_of_values, \
                                        DIRECT_HONEY_BADGERFISH, \
                                        _LITERAL_META_PAT, \
                                        _RESOURCE_META_PAT

from peyotl.utility import get_logger
_LOG = get_logger(__name__)

_SUPPRESSED_LITERAL = frozenset(['@datatype', '@property', '@xsi:type', '$'])
_SUPPRESSED_RESOURCE = frozenset(['@rel', '@property', '@xsi:type'])

class Badgerfish2DirectNexson(NexsonConverter):
    '''Conversion of the direct Badgerfish and Phylografter JSON
    to the direct form of honeybadgerfish JSON (v 1.0)
    This is a dict-to-dict in-place conversion. No serialization is included.
    '''
    def __init__(self, conv_cfg):
        NexsonConverter.__init__(self, conv_cfg)
        self._from_phylografter = conv_cfg.get('_from_phylografter', True)
        if self._from_phylografter:
            self._workaround_phylografter_rel_bug = True # pg uses "property" instead of "rel"
            self._add_tree_xsi_type = True
            self._coercing_literals = True # phylografter uses "true" for isLeaf
        else:
            self._workaround_phylografter_rel_bug = False
            self._add_tree_xsi_type = False

    def _transform_literal_meta(self, lit_bf_meta):
        dt = lit_bf_meta.get('@datatype')
        content = lit_bf_meta.get('$')
        att_key = lit_bf_meta['@property']
        full_obj = {}
        for k in lit_bf_meta.keys():
            if k not in _SUPPRESSED_LITERAL:
                full_obj[k] = lit_bf_meta[k]
        # Coercion should not be needed for json->json
        if dt and self._coercing_literals:
            if isinstance(content, str) or isinstance(content, unicode):
                content = _coerce_literal_val_to_primitive(dt, content)
        att_key = '^' + att_key
        if full_obj:
            if content:
                full_obj['$'] = content
            _cull_redundant_about(full_obj)
            return att_key, full_obj
        return att_key, content

    def _transform_resource_meta(self, res_bf_meta):
        try:
            att_key = res_bf_meta['@rel']
        except KeyError:
            if self._workaround_phylografter_rel_bug:
                att_key = res_bf_meta['@property']
            else:
                raise
        full_obj = {}
        for k in res_bf_meta.keys():
            if k not in _SUPPRESSED_RESOURCE:
                full_obj[k] = res_bf_meta[k]
        att_key = '^' + att_key
        assert full_obj
        _cull_redundant_about(full_obj)
        return att_key, full_obj

    def _recursive_convert_list(self, obj):
        for el in obj:
            if isinstance(el, dict):
                self._recursive_convert_dict(el)

    def _recursive_convert_dict(self, obj):
        _cull_redundant_about(obj) # rule 10...
        meta_list = _get_index_list_of_values(obj, 'meta')
        to_inject = {}
        for meta in meta_list:
            xt = meta['@xsi:type']
            if _RESOURCE_META_PAT.match(xt):
                mk, mv = self._transform_resource_meta(meta)
            else:
                assert _LITERAL_META_PAT.match(xt)
                mk, mv = self._transform_literal_meta(meta)
            _add_value_to_dict_bf(to_inject, mk, mv)
        if ('meta' in obj) and self.remove_old_structs:
            del obj['meta']
        for k, v in to_inject.items():
            _add_value_to_dict_bf(obj, k, v)
        for k, v in obj.items():
            if isinstance(v, dict):
                self._recursive_convert_dict(v)
            elif isinstance(v, list):
                self._recursive_convert_list(v)

    def _dict_to_list_of_dicts(self, obj, tag, child_tag=None, grand_child_tag=None):
        el = obj.get(tag)
        if el:
            if not isinstance(el, list):
                as_list = [el]
                if child_tag is None:
                    obj[tag] = as_list
                    return
            else:
                as_list = el
            if child_tag:
                for sub in as_list:
                    self._dict_to_list_of_dicts(sub, tag=child_tag, child_tag=grand_child_tag)

    def convert(self, obj):
        '''Takes a dict corresponding to the honeybadgerfish JSON blob of the 1.0.* type and
        converts it to BY_ID_HONEY_BADGERFISH version. The object is modified in place
        and returned.
        '''
        if self.pristine_if_invalid:
            raise NotImplementedError('pristine_if_invalid option is not supported yet')

        nex = get_nexml_el(obj)
        assert nex
        self._recursive_convert_dict(nex)
        # pluralization simplifications in hbf:
        # convert dicts to lists for the primary datastructures...
        self._dict_to_list_of_dicts(nex, 'otus')
        self._dict_to_list_of_dicts(nex, 'otus', 'otu')
        self._dict_to_list_of_dicts(nex, 'trees')
        self._dict_to_list_of_dicts(nex, 'trees', 'tree')
        self._dict_to_list_of_dicts(nex, 'trees', 'tree', 'node')
        self._dict_to_list_of_dicts(nex, 'trees', 'tree', 'edge')
        if self._add_tree_xsi_type:
            for tb in nex.get('trees', []):
                for t in tb.get('tree', []):
                    t.setdefault('@xsi:type', 'nex:FloatTree')
        nex['@nexml2json'] = str(DIRECT_HONEY_BADGERFISH)
        return obj
