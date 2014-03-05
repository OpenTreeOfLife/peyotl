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
def _get_par_obj_code(c):
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
        add_schema_attributes(self, self._nexson_version)
        assert(self._nexson_version[:3] in ('0.0', '1.0', '1.2'))
        self._validate_nexml_obj(self._nexml, anc=(obj, None))
    def _bf_meta_list_to_dict(self, m_list, par_obj_code, par, par_anc):
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
                self._error_event(par_obj_code,
                                  obj=par,
                                  err_type=gen_UnparseableMetaWarning,
                                  anc=par_anc,
                                  obj_nex_id=None,
                                  obj_list=unparseable_m)
        return d

    def _event_address(self, obj_code, obj, anc, obj_nex_id, anc_offset=0):
        pyid = id(obj)
        addr = self._pyid_to_nexson_add.get(pyid)
        if addr is None:
            if len(anc) > anc_offset:
                p_ind = -1 -anc_offset
                p, pnid = anc[p_ind]
                pea = self._event_address(_get_par_obj_code(obj_code),
                                          p,
                                          anc,
                                          pnid,
                                          1 + anc_offset)
                par_addr = pea[0]
            else:
                par_addr = None
            addr = LazyAddress(obj_code, obj=obj, obj_nex_id=obj_nex_id, par_addr=par_addr)
            self._pyid_to_nexson_add[pyid] = addr
        return addr, pyid
    def _warn_event(self, obj_code, obj, err_type, anc, obj_nex_id, *valist, **kwargs):
        c = factory2code[err_type]
        if not self._logger.is_logging_type(c):
            return
        address, pyid = self._event_address(obj_code, obj, anc, obj_nex_id)
        err_type(address, pyid, self._logger, SeverityCodes.WARNING, *valist, **kwargs)
    def _error_event(self, obj_code, obj, err_type, anc, obj_nex_id, *valist, **kwargs):
        c = factory2code[err_type]
        if not self._logger.is_logging_type(c):
            return
        address, pyid = self._event_address(obj_code, obj, anc, obj_nex_id)
        err_type(address, pyid, self._logger, SeverityCodes.ERROR, *valist, **kwargs)
    def _get_list_key(self, obj_code, obj, key, anc, obj_nex_id=None):
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
            self._error_event(obj_code,
                              obj=obj,
                              err_type=gen_MissingExpectedListWarning,
                              anc=anc,
                              obj_nex_id=obj_nex_id,
                              key_list=[key,])
            return None
        return k
    def _register_nexson_id(self, nid, nobj, anc, element_type=''):
        robj = self._nexson_id_to_obj.setdefault(nid, nobj)
        if robj is nobj:
            return True
        self._error_event(element_type,
                          obj=nobj,
                          err_type=gen_RepeatedIDWarning,
                          anc=anc,
                          obj_nex_id=nid,
                          key_list=[key])
        return False
    def _validate_obj_by_schema(self, obj_code, obj, anc, obj_nex_id, schema):
        '''Creates:
            errors if `obj` does not contain keys in the schema.ALLOWED_KEY_SET,
            warnings if `obj` lacks keys listed in schema.EXPECETED_KEY_SET, 
                      or if `obj` contains keys not listed in schema.ALLOWED_KEY_SET.
        '''
        wrong_type = []
        unrec_meta_keys = []
        unrec_non_meta_keys = []
        
        if self._using_hbf_meta:
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
            m = self._get_list_key(obj_code, obj, 'meta', anc)
            if m:
                # might want a flag of meta?
                md = self._bf_meta_list_to_dict(m, obj_code, obj, anc)
                mrmk = [i for i in schema.REQUIRED_META_KEY_SET if i not in md]
                memk = [i for i in schema.EXPECTED_META_KEY_SET if i not in md]
                if memk:
                    self._warn_event(obj_code,
                                     obj=obj,
                                     err_type=gen_MissingOptionalKeyWarning,
                                     anc=anc,
                                     obj_nex_id=obj_nex_id,
                                     key_list=memk)
                if mrmk:
                    self._error_event(obj_code,
                                     obj=obj,
                                     err_type=gen_MissingMandatoryKeyWarning,
                                     anc=anc,
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
            self._error_event(obj_code,
                             obj=obj,
                             err_type=gen_WrongValueTypeWarning,
                             anc=anc,
                             obj_nex_id=obj_nex_id,
                             key_val_type_list=wrong_type)
        if unrec_non_meta_keys:
            self._warn_event(obj_code,
                             obj=obj,
                             err_type=gen_UnrecognizedKeyWarning,
                             anc=anc,
                             obj_nex_id=obj_nex_id,
                             key_list=unrec_non_meta_keys)
        if unrec_meta_keys:
            # might want a flag of meta?
            self._warn_event(obj_code,
                             obj=obj,
                             err_type=gen_UnrecognizedKeyWarning,
                             anc=anc,
                             obj_nex_id=obj_nex_id,
                             key_list=unrec_meta_keys)

        off_key = [k for k in schema.EXPECETED_KEY_SET if k not in obj]
        if off_key:
            self._warn_event(obj_code,
                             obj=obj,
                             err_type=gen_MissingOptionalKeyWarning,
                             anc=anc,
                             obj_nex_id=obj_nex_id,
                             key_list=off_key)
        off_key = [k for k in schema.REQUIRED_KEY_SET if k not in obj]
        if off_key:
            self._error_event(obj_code,
                             obj=obj,
                             err_type=gen_MissingMandatoryKeyWarning,
                             anc=anc,
                             obj_nex_id=obj_nex_id,
                             key_list=off_key)

    def _validate_nexml_obj(self, nex_obj, anc):
        schema = self._NexmlEl_Schema
        anc_l = [anc]
        nid = nex_obj.get('@id')
        if nid is not None:
            self._register_nexson_id(nid, nex_obj, anc, _NEXEL_NEXML)
        self._validate_obj_by_schema(_NEXEL_NEXML, nex_obj, anc_l, nid, schema)
        return self._post_key_check_validate_nexml_obj(nex_obj, nid, anc_l)
    def _validate_otus_group_list(self, otu_group_id_obj_list, anc_list):
        for el in otu_group_id_obj_list:
            if not self._register_nexson_id(el[0], el[1], anc_list, _NEXEL_OTUS):
                return False
        schema = self._OtusEl_Schema
        for el in otu_group_id_obj_list:
            ogid = el[0]
            og = el[1]
            self._validate_obj_by_schema(_NEXEL_OTUS, og, anc_list, ogid, schema)
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

    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, anc_list):
        otus_group_list = nex_obj.get('otus')
        if otus_group_list and isinstance(otus_group_list, dict):
            otus_group_list = [otus_group_list]
        if not otus_group_list:
            self._error_event(_NEXEL_NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['otus'])
            return False
        anc_list.append((nex_obj, obj_nex_id))
        without_id = []
        og_tuple_list = []
        for og in otus_group_list:
            ogid = og.get('@id')
            if ogid is None:
                without_id.append(og)
            else:
                og_tuple_list.append((ogid, og))
        if without_id:
            self._error_event(_NEXEL_NEXML,
                             obj=without_id,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=anc_list,
                             key_list=['@id'])
            return False
        return self._validate_otus_group_list(og_tuple_list, anc_list)

class DirectHBFValidationAdaptor(BadgerFishValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)

class ByIdHBFValidationAdaptor(NexsonValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)

    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, anc_list):
        otus = nex_obj.get('otusById')
        otus_order_list = nex_obj.get('^ot:otusElementOrder')
        if (not otus) or (not isinstance(otus, dict)) \
          or (not otus_order_list) or (not isinstance(otus_order_list, list)):
            self._error_event(_NEXEL_NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=anc_list,
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
                             anc=anc_list,
                             key_list=missing_ogid)
            return False
        anc_list.append((nex_obj, obj_nex_id))
        if not_dict_og:
            self._error_event(_NEXEL_OTUS,
                             obj=otus,
                             err_type=gen_WrongValueTypeWarning,
                             anc=anc_list,
                             key_val_type_list=[not_dict_og])
            return False
        return self._validate_otus_group_list(otus_group_list, anc_list)
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
