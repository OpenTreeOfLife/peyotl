#!/usr/bin/env python
import json
from peyotl.nexson_validation.helper import SeverityCodes, _NEXEL
from peyotl.nexson_validation.schema import add_schema_attributes, check_raw_dict
from peyotl.nexson_validation.err_generator import factory2code, \
                                                   gen_MissingCrucialContentWarning, \
                                                   gen_MissingExpectedListWarning, \
                                                   gen_MissingMandatoryKeyWarning, \
                                                   gen_MissingOptionalKeyWarning, \
                                                   gen_MultipleRootsWarning, \
                                                   gen_NoRootWarning, \
                                                   gen_ReferencedIDNotFoundWarning, \
                                                   gen_RepeatedIDWarning, \
                                                   gen_UnparseableMetaWarning, \
                                                   gen_UnrecognizedKeyWarning, \
                                                   gen_WrongValueTypeWarning
from peyotl.nexson_syntax.helper import get_nexml_el, \
                                        extract_meta, \
                                        _add_value_to_dict_bf, \
                                        _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf
from peyotl.nexson_syntax import detect_nexson_version
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

_EMPTY_TUPLE = tuple()
_USING_IDREF_ONLY_PATHS = True

class LazyAddress(object):
    @staticmethod
    def _address_code_to_str(code):
        return _NEXEL.CODE_TO_STR[code]
    def __init__(self, code, obj=None, obj_nex_id=None, par_addr=None):
        assert(code in _NEXEL.CODE_TO_STR)
        self.code = code
        self.ref = obj
        if obj_nex_id is None:
            self.obj_nex_id = obj.get('@id')
        else:
            self.obj_nex_id = obj_nex_id
        self.par_addr = par_addr
        self._path, self._full_path = None, None
    def write_path_suffix_str(self, out):
        p = self.path
        out.write(' in ')
        out.write(p)
    def get_full_path(self):
        if self._full_path is None:
            if self.par_addr is None:
                assert(self.code == _NEXEL.TOP_LEVEL)
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
                        assert(self.code == _NEXEL.TOP_LEVEL)
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
                    assert(self.code == _NEXEL.TOP_LEVEL)
                    self._path = {}
                else:
                    #_LOG.debug('par ' + str(self.par_addr.path))
                    self._path = dict(self.par_addr.path)
                self._path['@top'] = _NEXEL.CODE_TO_TOP_ENTITY_NAME[self.code]
                if self.obj_nex_id is not None:
                    self._path['@idref'] = self.obj_nex_id
                    other_id_key = _NEXEL.CODE_TO_OTHER_ID_KEY[self.code]
                    if other_id_key is not None:
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
        assert(self.schema is not None)
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

class NexsonValidationAdaptor(object):
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
        self._otu_by_otug = {}
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
            assert(isinstance(self._nexml, dict))
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
        
        try:
            # a little duck-punching
            vc = _ValidationContext(self, logger)
            add_schema_attributes(vc, self._nexson_version)
            assert(self._nexson_version[:3] in ('0.0', '1.0', '1.2'))
            self._validate_nexml_obj(self._nexml, vc, obj)
        finally:
            vc.adaptor = None # delete circular ref to help gc
            del vc
            del self._otu_group_by_id
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

    def _event_address(self, element_type, obj, anc, obj_nex_id, anc_offset=0):
        pyid = id(obj)
        addr = self._pyid_to_nexson_add.get(pyid)
        if addr is None:
            if len(anc) > anc_offset:
                p_ind = -1 -anc_offset
                p, pnid = anc[p_ind]
                pea = self._event_address(self._get_par_element_type(element_type),
                                          p,
                                          anc,
                                          pnid,
                                          1 + anc_offset)
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
        address, pyid = self._event_address(element_type, obj, anc, obj_nex_id)
        #_LOG.debug('err type = '+ str(err_type) + ' adaptor type = ' + str(type(self)))
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
        if pc is None:
            return self._meta_par_code_stash
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
                          key_list=[key])
        self._repeated_id = True
        return False
    def _validate_obj_by_schema(self, obj, obj_nex_id, vc):
        '''Creates:
            errors if `obj` does not contain keys in the schema.ALLOWED_KEY_SET,
            warnings if `obj` lacks keys listed in schema.EXPECETED_KEY_SET, 
                      or if `obj` contains keys not listed in schema.ALLOWED_KEY_SET.
        '''
        return self._validate_id_obj_list_by_schema([(obj_nex_id, obj)], vc)
    def _validate_id_obj_list_by_schema(self, id_obj_list, vc):
        #TODO: should optimize for sets of objects with the same warnings...
        element_type = vc.curr_element_type
        assert(element_type is not None)
        anc_list = vc.anc_list
        schema = vc.schema
        #_LOG.debug('using schema type = ' + vc.schema_name())
        using_hbf_meta = vc._using_hbf_meta
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
                    mrmk = [i for i in schema.REQUIRED_META_KEY_SET if i not in md]
                    memk = [i for i in schema.EXPECTED_META_KEY_SET if i not in md]
                    if memk:
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
        return True
    def _validate_nexml_obj(self, nex_obj, vc, top_obj):
        vc.push_context(_NEXEL.NEXML, (top_obj, None))
        try:
            nid = nex_obj.get('@id')
            if nid is not None:
                self._register_nexson_id(nid, nex_obj, vc)
            self._validate_obj_by_schema(nex_obj, nid, vc)
            return self._post_key_check_validate_nexml_obj(nex_obj, nid, vc)
        finally:
          vc.pop_context()
    def _validate_otus_group_list(self, otu_group_id_obj_list, vc):
        for el in otu_group_id_obj_list:
            ogid, og = el
            if not self._register_nexson_id(ogid, og, vc):
                return False
            self._validate_obj_by_schema(og, ogid, vc)
            self._post_key_check_validate_otus_obj(ogid, og, vc)
        return True

    def _validate_trees_group_list(self, trees_group_id_obj_list, vc):
        for el in trees_group_id_obj_list:
            tgid, tg = el
            if not self._register_nexson_id(tgid, tg, vc):
                return False
            self._validate_obj_by_schema(tg, tgid, vc)
            self._post_key_check_validate_tree_group(tgid, tg, vc)
        return True

    def _validate_tree(self, tree_id, tree_obj, vc):
        if not self._register_nexson_id(tree_id, tree_obj, vc):
            return False
        self._validate_obj_by_schema(tree_obj, tree_id, vc)
        self._post_key_check_validate_tree(tree_id, tree_obj, vc)
        return True

    def _validate_leaf_list(self, leaf_id_obj_list, vc):
        vc.push_context_no_anc(_NEXEL.LEAF_NODE)
        try:
            self._validate_id_obj_list_by_schema(leaf_id_obj_list, vc)
        finally:
            vc.pop_context_no_anc()
        return True
    def _validate_internal_node_list(self, node_id_obj_list, vc):
        vc.push_context_no_anc(_NEXEL.INTERNAL_NODE)
        try:
            self._validate_id_obj_list_by_schema(node_id_obj_list, vc)
        finally:
            vc.pop_context_no_anc()
        return True
    def _validate_edge_list(self, edge_id_obj_list, vc):
        vc.push_context_no_anc(_NEXEL.EDGE)
        try:
            self._validate_id_obj_list_by_schema(edge_id_obj_list, vc)
        finally:
            vc.pop_context_no_anc()
        return True
    
    def _validate_otu_group_list(self, otu_id_obj_list, vc):
        for el in otu_id_obj_list:
            ogid, og = el
            if not self._register_nexson_id(ogid, og, vc):
                return False
            self._otu_group_by_id[ogid] = og
        #_LOG.debug(str(otu_id_obj_list))
        self._validate_id_obj_list_by_schema(otu_id_obj_list, vc)
        self._post_key_check_validate_otu_id_obj_list(otu_id_obj_list, vc)
        return True
    def _post_key_check_validate_otu_id_obj_list(self, otu_id_obj_list, vc):
        return True

    def add_or_replace_annotation(self, annotation):
        '''Takes an `annotation` dictionary which is 
        expected to have a string as the value of annotation['author']['name']
        This function will remove all annotations from obj that:
            1. have the same author/name, and
            2. have no messages that are flagged as messages to be preserved (values for 'preserve' that evaluate to true)
        '''
        return # TODO!
        # script_name = annotation['author']['name']
        # n = obj['nexml']
        # former_meta = n.setdefault('meta', [])
        # if not isinstance(former_meta, list):
        #     former_meta = [former_meta]
        #     n['meta'] = former_meta
        # else:
        #     indices_to_pop = []
        #     for annotation_ind, el in enumerate(former_meta):
        #         try:
        #             if (el.get('$') == annotation_label) and (el.get('author',{}).get('name') == script_name):
        #                 m_list = el.get('messages', [])
        #                 to_retain = []
        #                 for m in m_list:
        #                     if m.get('preserve'):
        #                         to_retain.append(m)
        #                 if len(to_retain) == 0:
        #                     indices_to_pop.append(annotation_ind)
        #                 elif len(to_retain) < len(m_list):
        #                     el['messages'] = to_retain
        #                     el['dateModified'] = datetime.datetime.utcnow().isoformat()
        #         except:
        #             # different annotation structures could yield IndexErrors or other exceptions.
        #             # these are not the annotations that you are looking for....
        #             pass

        #     if len(indices_to_pop) > 0:
        #         # walk backwards so pops won't change the meaning of stored indices
        #         for annotation_ind in indices_to_pop[-1::-1]:
        #             former_meta.pop(annotation_ind)
        # former_meta.append(annotation)
    def get_nexson_str(self):
        return json.dumps(self._raw, sort_keys=True, indent=0)
