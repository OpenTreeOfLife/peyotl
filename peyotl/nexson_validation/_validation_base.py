#!/usr/bin/env python
import json
from peyotl.nexson_validation.helper import SeverityCodes, _NEXEL, errorReturn
from peyotl.nexson_validation.schema import add_schema_attributes
from peyotl.nexson_validation.err_generator import factory2code, \
                                                   gen_MissingExpectedListWarning, \
                                                   gen_MissingMandatoryKeyWarning, \
                                                   gen_MissingOptionalKeyWarning, \
                                                   gen_MultipleTipsToSameOttIdWarning, \
                                                   gen_RepeatedIDWarning, \
                                                   gen_UnparseableMetaWarning, \
                                                   gen_UnrecognizedKeyWarning, \
                                                   gen_WrongValueTypeWarning
from peyotl.nexson_syntax.helper import add_literal_meta, \
                                        get_nexml_el, \
                                        find_val_literal_meta_first, \
                                        find_nested_meta_first, \
                                        extract_meta, \
                                        _add_value_to_dict_bf
from peyotl.nexson_syntax import detect_nexson_version
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

_EMPTY_TUPLE = tuple()
_USING_IDREF_ONLY_PATHS = False

def delete_same_agent_annotation(obj, annotation):
    agent_id = annotation.get('@wasAssociatedWithAgentId')
    delete_annotation(obj, agent_id=agent_id)

def delete_annotation(obj,
                      agent_id=None,
                      annot_id=None,
                      nexson_version=None):
    if nexson_version is None:
        nexson_version = detect_nexson_version(obj)
    nex_el = get_nexml_el(obj)
    annotation_list = get_annotation_list(nex_el, nexson_version)
    delete_annotation_from_annot_list(annotation_list, agent_id=agent_id, annot_id=annot_id)

def delete_annotation_from_annot_list(annotation_list, agent_id=None, annot_id=None):
    _LOG.debug('delete_annotation_from_annot_list with agent_id = ' + str(agent_id))
    to_remove_inds = []
    # TODO should check preserve field...
    if agent_id is not None:
        for n, annot in enumerate(annotation_list):
            if annot.get('@wasAssociatedWithAgentId') == agent_id:
                to_remove_inds.append(n)
    else:
        if annot_id is None:
            raise ValueError('Either agent_id or annot_id must have a value')
        for n, annot in enumerate(annotation_list):
            if annot.get('@id') == annot_id:
                to_remove_inds.append(n)
    while len(to_remove_inds) > 0:
        n = to_remove_inds.pop(-1)
        del annotation_list[n]


def replace_same_agent_annotation(obj, annotation):
    agent_id = annotation.get('@wasAssociatedWithAgentId')
    replace_annotation(obj, annotation, agent_id=agent_id)

def replace_annotation(obj,
                       annotation,
                       agent_id=None,
                       annot_id=None,
                       nexson_version=None):
    if nexson_version is None:
        nexson_version = detect_nexson_version(obj)
    nex_el = get_nexml_el(obj)
    annotation_list = get_annotation_list(nex_el, nexson_version)
    replace_annotation_from_annot_list(annotation_list, annotation, agent_id=agent_id, annot_id=annot_id)
    #_LOG.debug('oae = ' + str(find_nested_meta_first(nex_el, 'ot:annotationEvents', nexson_version)))

def get_annotation_list(nex_el, nexson_version):
    ae_s_obj = find_nested_meta_first(nex_el, 'ot:annotationEvents', nexson_version)
    if not ae_s_obj:
        ae_s_obj = add_literal_meta(nex_el, 'ot:annotationEvents', {'annotation':[]}, nexson_version)
    #_LOG.debug('ae_s_obj = ' + str(ae_s_obj))
    annotation_list = ae_s_obj.setdefault('annotation', [])
    #_LOG.debug('annotation_list = ' + str(annotation_list))
    return annotation_list

def replace_annotation_from_annot_list(annotation_list, annotation, agent_id=None, annot_id=None):
    to_remove_inds = []
    # TODO should check preserve field...
    if agent_id is not None:
        for n, annot in enumerate(annotation_list):
            if annot.get('@wasAssociatedWithAgentId') == agent_id:
                to_remove_inds.append(n)
    else:
        if annot_id is None:
            raise ValueError('Either agent_id or annot_id must have a value')
        for n, annot in enumerate(annotation_list):
            if annot.get('@id') == annot_id:
                to_remove_inds.append(n)
    while len(to_remove_inds) > 1:
        n = to_remove_inds.pop(-1)
        del annotation_list[n]
    if to_remove_inds:
        n = to_remove_inds.pop()
        annotation_list[n] = annotation
    else:
        annotation_list.append(annotation)
    #_LOG.debug('annotation_list = ' + str(annotation_list))

class LazyAddress(object):
    @staticmethod
    def _address_code_to_str(code):
        return _NEXEL.CODE_TO_STR[code]
    def __init__(self, code, obj=None, obj_nex_id=None, par_addr=None):
        assert code in _NEXEL.CODE_TO_STR
        self.code = code
        self.ref = obj
        #_LOG.debug('code={c} obj_nex_id = "{oni}"'.format(c=code, oni=obj_nex_id))
        if obj_nex_id is None:
            try:
                self.obj_nex_id = obj.get('@id')
            except:
                self.obj_nex_id = None
        else:
            self.obj_nex_id = obj_nex_id
        assert not isinstance(self.obj_nex_id, dict)
        self.par_addr = par_addr
        self._path, self._full_path = None, None
    def write_path_suffix_str(self, out):
        p = self.path
        out.write(' in ')
        out.write(p)
    def get_full_path(self):
        if self._full_path is None:
            if self.par_addr is None:
                assert self.code == _NEXEL.TOP_LEVEL
                self._full_path = {}
            else:
                #_LOG.debug('par ' + str(self.par_addr.path))
                self._full_path = dict(self.par_addr.get_full_path())
            self._full_path['@top'] = _NEXEL.CODE_TO_TOP_ENTITY_NAME[self.code]
            if self.obj_nex_id is not None:
                self._full_path['@idref'] = self.obj_nex_id
                other_id_key = _NEXEL.CODE_TO_OTHER_ID_KEY[self.code]
                if other_id_key is not None:
                    self._full_path[other_id_key] = self.obj_nex_id
            elif '@idref' in self._full_path:
                del self._full_path['@idref']
        return self._full_path
    def get_path(self):
        if self._path is None:
            if _USING_IDREF_ONLY_PATHS:
                if self.obj_nex_id is not None:
                    self._path = {'@idref': self.obj_nex_id}
                else:
                    if self.par_addr is None:
                        assert self.code == _NEXEL.TOP_LEVEL
                        self._path = {}
                    else:
                        #_LOG.debug('par ' + str(self.par_addr.path))
                        self._path = dict(self.par_addr.get_full_path())
                    self._path['@top'] = _NEXEL.CODE_TO_TOP_ENTITY_NAME[self.code]
                    if '@idref' in self._path:
                        del self._path['@idref']
            else:
                 #_LOG.debug('c = ' + str(self.code))
                if self.par_addr is None:
                    if self.code not in [None, _NEXEL.TOP_LEVEL]:
                        _LOG.debug('code = ' + _NEXEL.CODE_TO_STR[self.code])
                        assert self.code == _NEXEL.TOP_LEVEL
                    self._path = {}
                else:
                    #_LOG.debug('par ' + str(self.par_addr.path))
                    self._path = dict(self.par_addr.path)
                self._path['@top'] = _NEXEL.CODE_TO_TOP_ENTITY_NAME[self.code]
                if self.obj_nex_id is not None:
                    self._path['@idref'] = self.obj_nex_id
                    other_id_key = _NEXEL.CODE_TO_OTHER_ID_KEY[self.code]
                    if other_id_key is not None:
                        assert not isinstance(self.obj_nex_id, dict)
                        self._path[other_id_key] = self.obj_nex_id
                elif '@idref' in self._path:
                    del self._path['@idref']
        return self._path
    path = property(get_path)

class _ValidationContext(object):
    '''Holds references to the adaptor and logger
    '''
    _et2schema_name = {
        _NEXEL.NEXML: '_NexmlEl_Schema',
        _NEXEL.OTUS: '_OtusEl_Schema',
        _NEXEL.OTU: '_OtuEl_Schema',
        _NEXEL.TREES: '_TreesEl_Schema',
        _NEXEL.TREE: '_TreeEl_Schema',
        _NEXEL.NODE: '_NodeEl_Schema',
        _NEXEL.INTERNAL_NODE: '_IntNEl_Schema',
        _NEXEL.LEAF_NODE: '_LeafEl_Schema',
        _NEXEL.EDGE: '_EdgeEl_Schema',
    }
    def __init__(self, adaptor, logger):
        self.adaptor = adaptor
        self.logger = logger
        self.anc_list = []
        self.curr_element_type = _NEXEL.TOP_LEVEL
        self.schema = None
        self._element_type_stack = []
        self._schema_stack = []
    def push_context(self, element_type, new_par):
        assert len(new_par) == 2
        assert not isinstance(new_par[1], dict)
        self.anc_list.append(new_par)
        self.push_context_no_anc(element_type)
    def pop_context(self):
        prev_anc = self.anc_list.pop(-1)
        et = self.pop_context_no_anc()
        return et, prev_anc
    def push_context_no_anc(self, element_type):
        self._element_type_stack.append(self.curr_element_type)
        self._schema_stack.append(self.schema)
        self.curr_element_type = element_type
        self.schema = getattr(self, _ValidationContext._et2schema_name[element_type])
        assert self.schema is not None
    def pop_context_no_anc(self):
        et = self.curr_element_type
        self.curr_element_type = self._element_type_stack.pop(-1)
        self.schema = self._schema_stack.pop(-1)
        return et
    def schema_name(self):
        names = ['_NexmlEl_Schema',
                 '_OtusEl_Schema',
                 '_OtuEl_Schema',
                 '_TreesEl_Schema',
                 '_TreeEl_Schema',
                 '_LeafEl_Schema',
                 '_IntNEl_Schema',
                 '_EdgeEl_Schema']
        for n in names:
            if self.schema is getattr(self, n, -1):
                return n
        return ''

class NexsonAnnotationAdder(object):
    def add_or_replace_annotation(self,
                                  obj,
                                  annotation,
                                  agent,
                                  add_agent_only=False):
        '''Takes an `annotation` dictionary which is
        expected to have a string as the value of annotation['author']['name']
        This function will remove all annotations from obj that:
            1. have the same author/name, and
            2. have no messages that are flagged as messages to be preserved (values for 'preserve'
                that evaluate to true)
        '''
        nex = get_nexml_el(obj)
        nvers = detect_nexson_version(obj)
        _LOG.debug('detected version as ' + nvers)
        agents_obj = find_val_literal_meta_first(nex, 'ot:agents', nvers)
        if not agents_obj:
            agents_obj = add_literal_meta(nex, 'ot:agents', {'agent':[]}, nvers)
        agents_list = agents_obj.setdefault('agent', [])
        found_agent = False
        aid = agent['@id']
        for a in agents_list:
            if a.get('@id') == aid:
                found_agent = True
                break
        if not found_agent:
            agents_list.append(agent)
        if add_agent_only:
            delete_same_agent_annotation(obj, annotation)
        else:
            replace_same_agent_annotation(obj, annotation)

class NexsonValidationAdaptor(NexsonAnnotationAdder):
    '''An object created during NexSON validation.
    It holds onto the nexson object that it was instantiated for.
    When add_or_replace_annotation is called, it will annotate the
    nexson object, and when get_nexson_str is called it will
    serialize it.

    This class is useful merely because it allows the validation log
        and annotations to be relatively light weight, and yet easy
        to efficiently add back to the orignal NexSON object.
    '''
    def __init__(self, obj, logger):

        self._raw = obj
        self._nexml = None
        self._pyid_to_nexson_add = {}
        self._logger = logger
        self._repeated_id = False
        self._otuid2ottid_byogid = {}
        self._ottid2otuid_list_byogid = {}
        self._dupottid_by_ogid_tree_id = {}
        uk = None
        for k in obj.keys():
            if k not in ['nexml', 'nex:nexml']:
                if uk is None:
                    uk = []
                uk.append(k)
        if uk:
            uk.sort()
            self._warn_event(_NEXEL.TOP_LEVEL,
                             obj=obj,
                             err_type=gen_UnrecognizedKeyWarning,
                             anc=_EMPTY_TUPLE,
                             obj_nex_id=None,
                             key_list=uk)
        self._nexml = None
        try:
            self._nexml = get_nexml_el(obj)
            assert isinstance(self._nexml, dict)
        except:
            self._error_event(_NEXEL.TOP_LEVEL,
                              obj=obj,
                              err_type=gen_MissingMandatoryKeyWarning,
                              anc=_EMPTY_TUPLE,
                              obj_nex_id=None,
                              key_list=['nexml',])
            return ## EARLY EXIT!!
        self._nexson_id_to_obj = {}
        self._nexson_version = detect_nexson_version(obj)

        #attr used in validation only should be cleaned up
        # in the finally clause
        self._otu_group_by_id = {}
        self._otu_by_otug = {}

        try:
            # a little duck-punching
            vc = _ValidationContext(self, logger)
            add_schema_attributes(vc, self._nexson_version)
            assert self._nexson_version[:3] in ('0.0', '1.0', '1.2')
            self._validate_nexml_obj(self._nexml, vc, obj)
        finally:
            vc.adaptor = None # delete circular ref to help gc
            del vc
            del self._otu_group_by_id
            del self._otu_by_otug

    def _fill_otu_ottid_maps(self, otus_group_id):
        if self._otuid2ottid_byogid.get(otus_group_id) is None:
            otuid2ottid = {}
            ottid2otuid_list = {}
            self._otuid2ottid_byogid[otus_group_id] = otuid2ottid
            self._ottid2otuid_list_byogid[otus_group_id] = ottid2otuid_list
            otu_dict = self._otu_by_otug[otus_group_id]
            for otuid, otu in otu_dict.items():
                ottid = find_val_literal_meta_first(otu, 'ot:ottId', self._nexson_version)
                otuid2ottid[otuid] = ottid
                ottid2otuid_list.setdefault(ottid, []).append(otuid)
            return otuid2ottid, ottid2otuid_list
        return self._otuid2ottid_byogid[otus_group_id], self._ottid2otuid_list_byogid[otus_group_id]

    def _detect_multilabelled_tree(self,
                                   otus_group_id,
                                   tree_id,
                                   otuid2leaf):
        # See if there are any otus that we need to flag as occurring in a tree
        # multiple_times
        #
        pair = self._fill_otu_ottid_maps(otus_group_id)
        ottid2otuid_list = pair[1]
        dup_dict = {}
        nd_list = None
        for ottid, otuid_list in ottid2otuid_list.items():
            if isinstance(otuid_list, list) and len(otuid_list) > 1:
                if nd_list is None:
                    nd_list = []
                for otuid in otuid_list:
                    nd_id = otuid2leaf.get(otuid)
                    if nd_id is not None:
                        nd_list.append((otuid, nd_id))
                if len(nd_list) > 1:
                    dup_dict[ottid] = nd_list
                    nd_list = None
                else:
                    del nd_list[:]
        bt = self._dupottid_by_ogid_tree_id.setdefault(otus_group_id, {})
        bt[tree_id] = dup_dict


    def _generate_ott_warnings(self, ogid2og_map, used_tree_id_list, nex_tuple, vc):
        for ogid, by_tree in self._dupottid_by_ogid_tree_id.items():
            ottid2otuid_list = self._ottid2otuid_list_byogid[ogid]
            dup_ottid_set = set()
            for ottid, otuid_list in ottid2otuid_list.items():
                if isinstance(otuid_list, list) and len(otuid_list):
                    dup_ottid_set.add(ottid)
            otuid2dup_set = set()
            for dottid in dup_ottid_set:
                for tree_id in used_tree_id_list:
                    dup_dict = by_tree.get(tree_id, {})
                    nl = dup_dict.get(dottid)
                    if nl and len(nl) > 1:
                        otu_ids = [i[0] for i in nl] # (otu_id, no_id) pairs in nl
                        sotu = frozenset(otu_ids)
                        if sotu not in otuid2dup_set:
                            otuid2dup_set.add(sotu)
            if otuid2dup_set:
                vc.push_context(_NEXEL.OTUS, nex_tuple)
                try:
                    og = ogid2og_map[ogid]
                    for otu_set in otuid2dup_set:
                        self._warn_event(_NEXEL.OTUS,
                                          obj=og,
                                          err_type=gen_MultipleTipsToSameOttIdWarning,
                                          anc=vc.anc_list,
                                          obj_nex_id=ogid,
                                          otu_sets=list(otu_set))
                finally:
                    vc.pop_context()

    def _bf_meta_list_to_dict(self, m_list, par, par_vc):
        d = {}
        unparseable_m = None
        for m_el in m_list:
            try:
                n = m_el.get('@property')
            except:
                if unparseable_m is None:
                    unparseable_m = []
                unparseable_m.append(m_el)
            else:
                if n is None:
                    n = m_el.get('@rel')
                if n is None:
                    if unparseable_m is None:
                        unparseable_m = []
                    unparseable_m.append(m_el)
                else:
                    _add_value_to_dict_bf(d, n, m_el)
        if unparseable_m:
            for m_el in unparseable_m:
                self._error_event(par_vc.curr_element_type,
                                  obj=par,
                                  err_type=gen_UnparseableMetaWarning,
                                  anc=par_vc.anc_list,
                                  obj_nex_id=None,
                                  obj_list=unparseable_m)
        return d

    _LIST_ADDR_INCR = 0
    def _event_address(self, element_type, obj, anc, obj_nex_id, anc_offset=0):
        if isinstance(obj_nex_id, list):
            obj_nex_id.sort()
            pyid = (NexsonValidationAdaptor._LIST_ADDR_INCR, None)
            NexsonValidationAdaptor._LIST_ADDR_INCR += 1
        else:
            pyid = id(obj)
        addr = self._pyid_to_nexson_add.get(pyid)
        if addr is None:
            if len(anc) > anc_offset:
                p_ind = -1 -anc_offset
                p, pnid = anc[p_ind]
                #_LOG.debug('addr is None branch... anc = ' + str(anc))
                pea = self._event_address(element_type=self._get_par_element_type(element_type),
                                          obj=p,
                                          anc=anc,
                                          obj_nex_id=pnid,
                                          anc_offset=1 + anc_offset)
                par_addr = pea[0]
            else:
                par_addr = None
            addr = LazyAddress(element_type, obj=obj, obj_nex_id=obj_nex_id, par_addr=par_addr)
            self._pyid_to_nexson_add[pyid] = addr
        return addr, pyid
    def _warn_event(self, element_type, obj, err_type, anc, obj_nex_id, *valist, **kwargs):
        c = factory2code[err_type]
        if not self._logger.is_logging_type(c):
            return
        address, pyid = self._event_address(element_type, obj, anc, obj_nex_id)
        err_type(address, pyid, self._logger, SeverityCodes.WARNING, *valist, **kwargs)
    def _error_event(self, element_type, obj, err_type, anc, obj_nex_id, *valist, **kwargs):
        c = factory2code[err_type]
        if not self._logger.is_logging_type(c):
            return
        #_LOG.debug('in _error_event = ' + str(obj_nex_id))
        address, pyid = self._event_address(element_type, obj, anc, obj_nex_id)
        #_LOG.debug('in _error_event address.obj_nex_id = ' + str(address.obj_nex_id))
        err_type(address, pyid, self._logger, SeverityCodes.ERROR, *valist, **kwargs)
    def _get_list_key(self, obj, key, vc, obj_nex_id=None):
        '''Either:
            * Returns a list, or
            * Generates a MissingExpectedListWarning and returns None (if
                 the value is not a dict or list)
        '''
        k = obj.get(key)
        if k is None:
            return None
        if isinstance(k, dict):
            k = [k]
        if not isinstance(k, list):
            self._error_event(vc.curr_element_type,
                              obj=obj,
                              err_type=gen_MissingExpectedListWarning,
                              anc=vc.anc_list,
                              obj_nex_id=obj_nex_id,
                              key_list=[key,])
            return None
        return k

    def _get_par_element_type(self, c):
        pc = _NEXEL.CODE_TO_PAR_CODE.get(c)
        return pc

    def _check_meta_id(self, nid, meta_obj, k, container_obj, vc):
        robj = self._nexson_id_to_obj.setdefault(nid, meta_obj)
        if robj is meta_obj:
            return True
        self._error_event(vc.curr_element_type,
                          obj=meta_obj,
                          err_type=gen_RepeatedIDWarning,
                          anc=vc.anc_list,
                          obj_nex_id=nid,
                          key_list=[k])
        self._repeated_id = True
        return False
    def _register_nexson_id(self, nid, nobj, vc):
        robj = self._nexson_id_to_obj.setdefault(nid, nobj)
        if robj is nobj:
            return True
        self._error_event(vc.curr_element_type,
                          obj=nobj,
                          err_type=gen_RepeatedIDWarning,
                          anc=vc.anc_list,
                          obj_nex_id=nid,
                          key_list=[nid])
        self._repeated_id = True
        return False
    def _validate_obj_by_schema(self, obj, obj_nex_id, vc):
        '''Creates:
            errors if `obj` does not contain keys in the schema.ALLOWED_KEY_SET,
            warnings if `obj` lacks keys listed in schema.EXPECETED_KEY_SET,
                      or if `obj` contains keys not listed in schema.ALLOWED_KEY_SET.
        '''
        return self._validate_id_obj_list_by_schema([(obj_nex_id, obj)], vc, group_by_warning=False)
    def _validate_id_obj_list_by_schema(self, id_obj_list, vc, group_by_warning=False):
        #TODO: should optimize for sets of objects with the same warnings...
        element_type = vc.curr_element_type
        assert element_type is not None
        schema = vc.schema
        anc_list = vc.anc_list
        #_LOG.debug('using schema type = ' + vc.schema_name())
        using_hbf_meta = vc._using_hbf_meta
        _by_warn_type = {}
        for obj_nex_id, obj in id_obj_list:
            wrong_type = []
            unrec_meta_keys = []
            unrec_non_meta_keys = []

            if using_hbf_meta:
                for k, v in obj.items():
                    is_meta = k[0] == '^'
                    if k not in schema.ALLOWED_KEY_SET:
                        if is_meta:
                            unrec_meta_keys.append(k)
                        else:
                            unrec_non_meta_keys.append(k)
                    else:
                        correct_type, info = schema.K2VT[k](v, obj, k, vc)
                        if not correct_type:
                            wrong_type.append((k, v, info))
            else:
                for k, v in obj.items():
                    if k not in schema.ALLOWED_KEY_SET:
                        unrec_non_meta_keys.append(k)
                    else:
                        correct_type, info = schema.K2VT[k](v, obj, k, vc)
                        if not correct_type:
                            wrong_type.append((k, v, info))
                m = self._get_list_key(obj, 'meta', vc)
                if m:
                    # might want a flag of meta?
                    md = self._bf_meta_list_to_dict(m, obj, vc)
                    #_LOG.debug('md = ' + str(md))
                    mrmk = [i for i in schema.REQUIRED_META_KEY_SET if i not in md]
                    memk = [i for i in schema.EXPECTED_META_KEY_SET if i not in md]
                    if memk:
                        if group_by_warning:
                            memk.sort()
                            foks = frozenset(memk)
                            t = _by_warn_type.setdefault(foks, [[], []])
                            t[0].append(obj)
                            t[1].append(obj_nex_id)
                        else:
                            self._warn_event(element_type,
                                             obj=obj,
                                             err_type=gen_MissingOptionalKeyWarning,
                                             anc=anc_list,
                                             obj_nex_id=obj_nex_id,
                                             key_list=memk)
                    if mrmk:
                        self._error_event(element_type,
                                         obj=obj,
                                         err_type=gen_MissingMandatoryKeyWarning,
                                         anc=anc_list,
                                         obj_nex_id=obj_nex_id,
                                         key_list=mrmk)
                        msgf = 'missing mandatory meta key(s) according to {s} schema'
                        msg = msgf.format(s=vc.schema_name())
                        return errorReturn(msg)
                    for k, v in md.items():
                        if k not in schema.ALLOWED_META_KEY_SET:
                            unrec_meta_keys.append(k)
                        else:
                            #_LOG.debug('{k} --> "{v}"'.format(k=k, v=repr(v)))
                            correct_type, info = schema.K2VT[k](v, obj, k, vc)
                            if not correct_type:
                                v = extract_meta(v)
                                wrong_type.append((k, v, info))
            if wrong_type:
                self._error_event(element_type,
                                 obj=obj,
                                 err_type=gen_WrongValueTypeWarning,
                                 anc=anc_list,
                                 obj_nex_id=obj_nex_id,
                                 key_val_type_list=wrong_type)
                return errorReturn('wrong value type according to {s} schema'.format(s=vc.schema_name()))
            if unrec_non_meta_keys:
                self._warn_event(element_type,
                                 obj=obj,
                                 err_type=gen_UnrecognizedKeyWarning,
                                 anc=anc_list,
                                 obj_nex_id=obj_nex_id,
                                 key_list=unrec_non_meta_keys)
            if unrec_meta_keys:
                # might want a flag of meta?
                self._warn_event(element_type,
                                 obj=obj,
                                 err_type=gen_UnrecognizedKeyWarning,
                                 anc=anc_list,
                                 obj_nex_id=obj_nex_id,
                                 key_list=unrec_meta_keys)
            off_key = [k for k in schema.EXPECETED_KEY_SET if k not in obj]
            if off_key:
                if group_by_warning:
                    off_key.sort()
                    foks = frozenset(off_key)
                    t = _by_warn_type.setdefault(foks, [[], []])
                    t[0].append(obj)
                    t[1].append(obj_nex_id)
                else:
                    self._warn_event(element_type,
                                     obj=obj,
                                     err_type=gen_MissingOptionalKeyWarning,
                                     anc=anc_list,
                                     obj_nex_id=obj_nex_id,
                                     key_list=off_key)
            off_key = [k for k in schema.REQUIRED_KEY_SET if k not in obj]
            if off_key:
                self._error_event(element_type,
                                     obj=obj,
                                     err_type=gen_MissingMandatoryKeyWarning,
                                     anc=anc_list,
                                     obj_nex_id=obj_nex_id,
                                     key_list=off_key)
                return errorReturn('missing key(s) according to {s} schema'.format(s=vc.schema_name()))
        if _by_warn_type:
            for ks, obj_lists in _by_warn_type.items():
                mlist = list(ks)
                mlist.sort()
                id_arg = obj_lists[1]
                if len(id_arg) == 1:
                    id_arg = id_arg[0]
                obj_arg = obj_lists[0]
                if len(obj_arg) == 1:
                    obj_arg = obj_arg[0]
                self._warn_event(element_type,
                                 obj=obj_arg,
                                 err_type=gen_MissingOptionalKeyWarning,
                                 anc=anc_list,
                                 obj_nex_id=id_arg,
                                 key_list=mlist)
        return True
    def _validate_nexml_obj(self, nex_obj, vc, top_obj):
        vc.push_context(_NEXEL.NEXML, (top_obj, None))
        try:
            nid = nex_obj.get('@id')
            if nid is not None:
                if not self._register_nexson_id(nid, nex_obj, vc):
                    return False
            if not self._validate_obj_by_schema(nex_obj, nid, vc):
                return False
            return self._post_key_check_validate_nexml_obj(nex_obj, nid, vc)
        finally:
            vc.pop_context()
    def _validate_otus_group_list(self, otu_group_id_obj_list, vc):
        if not self._register_nexson_id_list(otu_group_id_obj_list, vc):
            return False
        for el in otu_group_id_obj_list:
            ogid, og = el
            self._otu_group_by_id[ogid] = og
            if not self._validate_obj_by_schema(og, ogid, vc):
                return False
            if not self._post_key_check_validate_otus_obj(ogid, og, vc):
                return False
        return True

    def _validate_trees_group_list(self, trees_group_id_obj_list, vc):
        if not self._register_nexson_id_list(trees_group_id_obj_list, vc):
            return False
        for el in trees_group_id_obj_list:
            tgid, tg = el
            if not self._validate_obj_by_schema(tg, tgid, vc):
                return False
            if not self._post_key_check_validate_tree_group(tgid, tg, vc):
                return False
        return True

    def _validate_tree(self, tree_id, tree_obj, vc, otus_group_id=None):
        if not self._register_nexson_id(tree_id, tree_obj, vc):
            return False
        if not self._validate_obj_by_schema(tree_obj, tree_id, vc):
            return False
        return self._post_key_check_validate_tree(tree_id,
                                                  tree_obj,
                                                  vc,
                                                  otus_group_id=otus_group_id)

    def _register_nexson_id_list(self, id_obj_list, vc):
        for obj_id, obj in id_obj_list:
            if not self._register_nexson_id(obj_id, obj, vc):
                return False
        return True

    def _validate_leaf_list(self, leaf_id_obj_list, vc):
        vc.push_context_no_anc(_NEXEL.LEAF_NODE)
        try:
            if not self._register_nexson_id_list(leaf_id_obj_list, vc):
                return False
            return self._validate_id_obj_list_by_schema(leaf_id_obj_list, vc)
        finally:
            vc.pop_context_no_anc()
        return not self._logger.has_error()
    def _validate_internal_node_list(self, node_id_obj_list, vc):
        vc.push_context_no_anc(_NEXEL.INTERNAL_NODE)
        try:
            if not self._register_nexson_id_list(node_id_obj_list, vc):
                return False
            return self._validate_id_obj_list_by_schema(node_id_obj_list, vc)
        finally:
            vc.pop_context_no_anc()
        return not self._logger.has_error()
    def _validate_node_list(self, node_id_obj_list, vc):
        vc.push_context_no_anc(_NEXEL.NODE)
        try:
            if not self._register_nexson_id_list(node_id_obj_list, vc):
                return False
            return self._validate_id_obj_list_by_schema(node_id_obj_list, vc)
        finally:
            vc.pop_context_no_anc()
        return not self._logger.has_error()
    def _validate_edge_list(self, edge_id_obj_list, vc):
        vc.push_context_no_anc(_NEXEL.EDGE)
        try:
            if not self._register_nexson_id_list(edge_id_obj_list, vc):
                return False
            return self._validate_id_obj_list_by_schema(edge_id_obj_list, vc)
        finally:
            vc.pop_context_no_anc()
        return not self._logger.has_error()

    def _validate_otu_list(self, otu_id_obj_list, vc):
        if not self._register_nexson_id_list(otu_id_obj_list, vc):
            return False
        #_LOG.debug(str(otu_id_obj_list))
        if not self._validate_id_obj_list_by_schema(otu_id_obj_list, vc, group_by_warning=True):
            return False
        return self._post_key_check_validate_otu_id_obj_list(otu_id_obj_list, vc)

    def _post_key_check_validate_otu_id_obj_list(self, otu_id_obj_list, vc):
        return True
    def _post_key_check_validate_tree(self,
                                      tree_nex_id,
                                      tree_obj,
                                      vc,
                                      otus_group_id=None):
        raise NotImplementedError('base NexsonValidationAdaptor hook')
    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, vc):
        raise NotImplementedError('base NexsonValidationAdaptor hook')
    def _post_key_check_validate_otus_obj(self, og_nex_id, otus_group, vc):
        raise NotImplementedError('base NexsonValidationAdaptor hook')
    def _post_key_check_validate_tree_group(self, tg_nex_id, trees_group, vc):
        raise NotImplementedError('base NexsonValidationAdaptor hook')

    def get_nexson_str(self):
        return json.dumps(self._raw, sort_keys=True, indent=0)
