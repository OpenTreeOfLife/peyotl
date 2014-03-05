#!/usr/bin/env python
'''NexsonValidationAdaptor class.
'''
import json
from peyotl.utility import get_logger
from peyotl.nexson_validation.helper import SeverityCodes
from peyotl.nexson_validation.schema import add_schema_attributes
from peyotl.nexson_validation.err_generator import factory2code, \
                                                   gen_MissingCrucialContentWarning, \
                                                   gen_MissingExpectedListWarning, \
                                                   gen_MissingMandatoryKeyWarning, \
                                                   gen_MissingOptionalKeyWarning, \
                                                   gen_ReferencedIDNotFoundWarning, \
                                                   gen_RepeatedIDWarning, \
                                                   gen_UnparseableMetaWarning, \
                                                   gen_UnrecognizedKeyWarning, \
                                                   gen_WrongValueTypeWarning
from peyotl.nexson_syntax.helper import get_nexml_el, \
                                        _add_value_to_dict_bf, \
                                        _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf

from peyotl.nexson_syntax import detect_nexson_version
_LOG = get_logger(__name__)
_NEXEL_TOP_LEVEL = 0
_NEXEL_NEXML = 1
_NEXEL_OTUS = 2
_NEXEL_OTU = 3
_NEXEL_TREES = 4
_NEXEL_TREE = 5
_NEXEL_NODE = 6
_NEXEL_EDGE = 7
_NEXEL_META = 8

_NEXEL_CODE_TO_STR = {
    _NEXEL_TOP_LEVEL: 'top-level',
    _NEXEL_NEXML: 'nexml',
    _NEXEL_OTUS: 'otus',
    _NEXEL_OTU: 'otu',
    _NEXEL_TREES: 'trees',
    _NEXEL_TREE: 'tree',
    _NEXEL_NODE: 'node',
    _NEXEL_EDGE: 'edge',
    _NEXEL_META: 'meta',
}
_NEXEL_CODE_TO_PAR_CODE = {
    _NEXEL_TOP_LEVEL: None,
    _NEXEL_NEXML: _NEXEL_TOP_LEVEL,
    _NEXEL_OTUS: _NEXEL_NEXML,
    _NEXEL_OTU: _NEXEL_OTUS,
    _NEXEL_TREES: _NEXEL_NEXML,
    _NEXEL_TREE: _NEXEL_TREES,
    _NEXEL_NODE: _NEXEL_TREE,
    _NEXEL_EDGE: _NEXEL_TREE,
}
_NEXEL_CODE_TO_OTHER_ID_KEY = {
    _NEXEL_TOP_LEVEL: None,
    _NEXEL_NEXML: None,
    _NEXEL_OTUS: '@otusID',
    _NEXEL_OTU: '@otuID',
    _NEXEL_TREES: '@treesID',
    _NEXEL_TREE: '@treeID',
    _NEXEL_NODE: '@nodeID',
    _NEXEL_EDGE: '@edgeID',
}
_NEXEL_CODE_TO_TOP_ENTITY_NAME = {
    _NEXEL_TOP_LEVEL: '',
    _NEXEL_NEXML: 'nexml',
    _NEXEL_OTUS: 'otus',
    _NEXEL_OTU: 'otus',
    _NEXEL_TREES: 'trees',
    _NEXEL_TREE: 'trees',
    _NEXEL_NODE: 'trees',
    _NEXEL_EDGE: 'trees',
}
def _get_par_element_type(c):
    pc = _NEXEL_CODE_TO_PAR_CODE[c]
    if pc is None:
        return None
    return pc

class LazyAddress(object):
    @staticmethod
    def _address_code_to_str(code):
        return _NEXEL_CODE_TO_STR[code]
    def __init__(self, code, obj=None, obj_nex_id=None, par_addr=None):
        assert(code in _NEXEL_CODE_TO_STR)
        self.code = code
        self.ref = obj
        if obj_nex_id is None:
            self.obj_nex_id = obj.get('@id')
        else:
            self.obj_nex_id = obj_nex_id
        self.par_addr = par_addr
        self._path = None
    def write_path_suffix_str(self, out):
        p = self.path
        out.write(' in ')
        out.write(p)
    def get_path(self):
        if self._path is None:
            if self.par_addr is None:
                assert(self.code == _NEXEL_TOP_LEVEL)
                self._path = {}
            else:
                self._path = dict(self.par_addr.path)
            self._path['@top'] = _NEXEL_CODE_TO_TOP_ENTITY_NAME[self.code]
            if self.obj_nex_id is not None:
                self._path['@idref'] = self.obj_nex_id
                other_id_key = _NEXEL_CODE_TO_OTHER_ID_KEY[self.code]
                if other_id_key is not None:
                    self._path[other_id_key] = self.obj_nex_id
            elif '@idref' in self._path:
                del self._path['@idref']
        return self._path
    path = property(get_path)

_EMPTY_TUPLE = tuple()

class _ValidationContext(object):
    '''Holds references to the adaptor and logger
    '''
    _et2schema_name = {
        _NEXEL_NEXML: '_NexmlEl_Schema',
        _NEXEL_OTUS: '_OtusEl_Schema',
        _NEXEL_OTU: '_OtuEl_Schema'
    }
    def __init__(self, adaptor, logger):
        self.adaptor = adaptor
        self.logger = logger
        self.anc_list = []
        self.curr_element_type = _NEXEL_TOP_LEVEL
        self.schema = None
    def switch_context(self, element_type, new_par):
        self.curr_element_type = element_type
        if new_par is None:
            self.anc_list.pop(-1)
        else:
            self.anc_list.append(new_par)
        self.schema = getattr(self, _ValidationContext._et2schema_name[element_type])
        
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
        uk = None
        for k in obj.keys():
            if k not in ['nexml', 'nex:nexml']:
                if uk is None:
                    uk = []
                uk.append(k)
        if uk:
            uk.sort()
            self._warn_event(_NEXEL_TOP_LEVEL,
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
            self._error_event(_NEXEL_TOP_LEVEL, 
                              obj=obj,
                              err_type=gen_MissingMandatoryKeyWarning,
                              anc=_EMPTY_TUPLE,
                              obj_nex_id=None,
                              key_list=['nexml',])
            return ## EARLY EXIT!!
        self._nexson_id_to_obj = {}
        self._nexson_version = detect_nexson_version(obj)
        # a little duck-punching
        vc = _ValidationContext(self, logger)
        add_schema_attributes(vc, self._nexson_version)
        assert(self._nexson_version[:3] in ('0.0', '1.0', '1.2'))
        self._validate_nexml_obj(self._nexml, vc, obj)

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
                pea = self._event_address(_get_par_element_type(element_type),
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
        anc_list = vc.anc_list
        schema = vc.schema
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
                        correct_type, info = schema.K2VT[k](v)
                        if not correct_type:
                            wrong_type.append((k, v, info))
            else:
                for k, v in obj.items():
                    if k not in schema.ALLOWED_KEY_SET:
                        unrec_non_meta_keys.append(k)
                    else:
                        correct_type, info = schema.K2VT[k](v)
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
                            correct_type, info = schema.K2VT[k](v)
                            if not correct_type:
                                v = schema._VT._extract_meta(v)
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
        vc.switch_context(_NEXEL_NEXML, (top_obj, None))
        nid = nex_obj.get('@id')
        if nid is not None:
            self._register_nexson_id(nid, nex_obj, vc)
        self._validate_obj_by_schema(nex_obj, nid, vc)
        return self._post_key_check_validate_nexml_obj(nex_obj, nid, vc)
    def _validate_otus_group_list(self, otu_group_id_obj_list, vc):
        for el in otu_group_id_obj_list:
            if not self._register_nexson_id(el[0], el[1], vc):
                return False
        for el in otu_group_id_obj_list:
            ogid = el[0]
            og = el[1]
            self._validate_obj_by_schema(og, ogid, vc)
            self._post_key_check_validate_otus_obj(og, ogid, vc)
        return True
    def _validate_otu_group_list(self, otu_id_obj_list, vc):
        for el in otu_id_obj_list:
            if not self._register_nexson_id(el[0], el[1], vc):
                return False
        self._validate_id_obj_list_by_schema(otu_id_obj_list, vc)
        self._post_key_check_validate_otu__id_obj_list(otu_id_obj_list, vc)
        return True
    def _post_key_check_validate_otu__id_obj_list(self, otu_id_obj_list, vc):
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

class BadgerFishValidationAdaptor(NexsonValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)

    def _post_key_check_validate_otus_obj(self, otus_group, og_nex_id, vc):
        otu_list = otus_group.get('otu')
        if otu_list and isinstance(otu_list, dict):
            otu_list = [otu_list]
        if not otu_list:
            self._error_event(_NEXEL_OTUS,
                             obj=otus_group,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=og_nex_id,
                             key_list=['otu'])
            return False
        vc.switch_context(_NEXEL_OTU, (otus_group, og_nex_id))
        without_id = []
        otu_tuple_list = []
        for otu in otu_list:
            oid = otu.get('@id')
            if oid is None:
                without_id.append(otu)
            else:
                otu_tuple_list.append((oid, otu))
        if without_id:
            self._error_event(_NEXEL_NEXML,
                             obj=without_id,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             key_list=['@id'])
            return False
        return self._validate_otu_group_list(otu_tuple_list, vc)
    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, vc):
        otus_group_list = nex_obj.get('otus')
        if otus_group_list and isinstance(otus_group_list, dict):
            otus_group_list = [otus_group_list]
        if not otus_group_list:
            self._error_event(_NEXEL_NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['otus'])
            return False
        vc.switch_context(_NEXEL_OTUS, (nex_obj, obj_nex_id))
        without_id = []
        og_tuple_list = []
        for og in otus_group_list:
            ogid = og.get('@id')
            if ogid is None:
                without_id.append(og)
            else:
                og_tuple_list.append((ogid, og))
        if without_id:
            self._error_event(_NEXEL_OTUS,
                             obj=without_id,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             key_list=['@id'])
            return False
        return self._validate_otus_group_list(og_tuple_list, vc)

class DirectHBFValidationAdaptor(BadgerFishValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)

class ByIdHBFValidationAdaptor(NexsonValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)
    def _post_key_check_validate_otus_obj(self, otus_group, og_nex_id, vc):
        otu_obj = otus_group.get('otuById')
        if (not otu_obj) or (not isinstance(otu_obj, dict)):
            self._error_event(_NEXEL_OTUS,
                             obj=otus_group,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=og_nex_id,
                             key_list=['otuById'])
            return False
        vc.switch_context(_NEXEL_OTU, (otus_group, og_nex_id))
        not_dict_otu = []
        otu_id_obj_list = []
        for id_obj_pair in otu_obj.items():
            if not isinstance(id_obj_pair[1], dict):
                # temp external use of _VT
                vt = self._NexmlEl_Schema._VT
                r = vt.DICT(id_obj_pair[1])
                assert(r[0] is False)
                t = r[1]
                not_dict_otu.append(t)
            else:
                otu_id_obj_list.append(id_obj_pair)
        if not_dict_otu:
            self._error_event(_NEXEL_OTU,
                             obj=otu_obj,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             key_val_type_list=[not_dict_otu])
            return False
        return self._validate_otu_group_list(otu_id_obj_list, vc)

    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, vc):
        otus = nex_obj.get('otusById')
        otus_order_list = nex_obj.get('^ot:otusElementOrder')
        if (not otus) or (not isinstance(otus, dict)) \
          or (not otus_order_list) or (not isinstance(otus_order_list, list)):
            self._error_event(_NEXEL_NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['otusById', '^ot:otusElementOrder'])
            return False
        otus_group_list = []
        missing_ogid = []
        not_dict_og = []
        for ogid in otus_order_list:
            og = otus.get(ogid)
            if og is None:
                missing_ogid.append(ogid)
            elif not isinstance(og, dict):
                # temp external use of _VT
                vt = self._NexmlEl_Schema._VT
                r = vt.DICT(og)
                assert(r[0] is False)
                t = r[1]
                not_dict_og.append(t)
            else:
                otus_group_list.append((ogid, og))
        if missing_ogid:
            self._error_event(_NEXEL_NEXML,
                             obj=nex_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             key_list=missing_ogid)
            return False
        vc.switch_context(_NEXEL_OTUS, (nex_obj, obj_nex_id))
        if not_dict_og:
            self._error_event(_NEXEL_OTUS,
                             obj=otus,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             key_val_type_list=[not_dict_og])
            return False
        return self._validate_otus_group_list(otus_group_list, vc)
def create_validation_adaptor(obj, logger):
    try:
        nexson_version = detect_nexson_version(obj)
    except:
        return BadgerFishValidationAdaptor(obj, logger)
    if _is_by_id_hbf(nexson_version):
        return ByIdHBFValidationAdaptor(obj, logger)
    elif _is_badgerfish_version(nexson_version):
        return BadgerFishValidationAdaptor(obj, logger)
    elif _is_direct_hbf(nexson_version):
        return DirectHBFValidationAdaptor(obj, logger)
    raise NotImplementedError('nexml2json version {v}'.format(v=nexson_version))
