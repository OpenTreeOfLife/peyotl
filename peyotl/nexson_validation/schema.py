#!/usr/bin/env python
from peyotl.nexson_syntax.helper import get_bf_meta_value, \
                                        _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

def add_schema_attributes(container, nexson_version):
    '''Adds several attributes to `container`:
    _using_hbf_meta  - boolean. True for HoneyBadgerFish v1-style meta elements ('^prop': value 
                rather than 'meta': {'$':value})
    and the following _SchemaFragment instances:
    _NexmlEl_Schema
    '''
    if _is_by_id_hbf(nexson_version):
        _add_by_id_nexson_schema_attributes(container)
    elif _is_badgerfish_version(nexson_version):
        _add_badgerfish_nexson_schema_attributes(container)
    elif _is_direct_hbf(nexson_version):
        _add_direct_nexson_schema_attributes(container)
    else:
        raise NotImplementedError('unrecognized nexson variant {}'.format(nexson_version))

class _SchemaFragment(object):
    def __init__(self,
                 required, 
                 expected,
                 allowed,
                 required_meta,
                 expected_meta,
                 type_checked_meta,
                 using_hbf_meta):
        '''
        `required` dict of key to _VT type code. Error is not present.
        `expected` dict of key to _VT type code. Warnings is not present.
        `allowed` dict of None ignored elements #@TODO could be a set.
        `required_meta` dict of meta key to _VT type code. Error is not present.
        `expected_meta` dict of meta key to _VT type code. Warnings is not present.
        `type_checked_meta` dict of meta key to _VT type code. Error if wrong type, no warning if absent.
        `using_hbf_meta` True for >=1.0.0, False for badgerfish.
        '''
        self.K2VT = dict(required)
        self.K2VT.update(expected)
        self.K2VT.update(allowed)

        required_meta_keys = tuple(required_meta.keys())
        expected_meta_keys = tuple(expected_meta.keys())
        required_keys = tuple(required.keys())
        expected_keys = tuple(expected.keys())
        allowed_keys = tuple(allowed.keys())
        if using_hbf_meta:
            for k, v in required_meta.items():
                self.K2VT['^' + k] = v
            for k, v in expected_meta.items():
                self.K2VT['^' + k] = v
            for k, v in type_checked_meta.items():
                self.K2VT['^' + k] = v
            self.REQUIRED_META_KEY_SET = frozenset(['^' + i for i in required_meta_keys])
            self.EXPECTED_META_KEY_SET = frozenset(['^' + i for i in expected_meta_keys])
            self.REQUIRED_KEY_SET = frozenset(required_keys + tuple(self.REQUIRED_META_KEY_SET))
            self.EXPECETED_KEY_SET = frozenset(expected_keys + tuple(self.EXPECTED_META_KEY_SET))
            self.ALLOWED_KEY_SET = frozenset(tuple(self.REQUIRED_KEY_SET) 
                                              + tuple(self.EXPECETED_KEY_SET) 
                                              + allowed_keys
                                              + tuple(['^' + i for i in type_checked_meta.keys()]))
        else:
            for k, v in required_meta.items():
                self.K2VT[k] = _VT.convert2meta(v)
            for k, v in expected_meta.items():
                self.K2VT[k] = _VT.convert2meta(v)
            for k, v in type_checked_meta.items():
                self.K2VT[k] = _VT.convert2meta(v)
            self.K2VT['meta'] = _VT.LIST_OR_DICT
            self.REQUIRED_META_KEY_SET = frozenset(required_meta_keys)
            self.EXPECTED_META_KEY_SET = frozenset(expected_meta_keys)
            self.ALLOWED_META_KEY_SET = frozenset(required_meta_keys + expected_meta_keys + tuple(type_checked_meta.keys()))
            self.REQUIRED_KEY_SET = frozenset(required_keys)
            self.EXPECETED_KEY_SET = frozenset(expected_keys)
            self.ALLOWED_KEY_SET = frozenset(('meta', ) 
                                              + tuple(self.REQUIRED_KEY_SET) 
                                              + tuple(self.EXPECETED_KEY_SET) 
                                              + allowed_keys)
        # for order-dependent
        x = list(self.REQUIRED_META_KEY_SET)
        x.sort()
        self.REQUIRED_META_KEY_TUPLE = tuple(x)
        x = list(self.EXPECTED_META_KEY_SET)
        x.sort()
        self.EXPECTED_META_KEY_TUPLE = tuple(x)
        x = list(self.ALLOWED_KEY_SET)
        x.sort()
        self.ALLOWED_KEY_TUPLE = tuple(x)
        x = list(self.REQUIRED_META_KEY_SET)
        x.sort()
        self.REQUIRED_META_TUPLE = tuple(x)
        x = list(self.EXPECTED_META_KEY_SET)
        x.sort()
        self.EXPECTED_META_KEY_TUPLE = tuple(x)
        self.USING_HBF_META = using_hbf_meta



class _VT:
    '''Value type enum'''
    __TRUE_VAL = (True, None)
    __FALSE_STR = (False, 'str')
    __FALSE_HREF = (False, 'href')
    __FALSE_LIST = (False, 'array')
    __FALSE_DICT = (False, 'object')
    __FALSE_STR_REPEATABLE_EL = (False, 'string or string array')
    __FALSE_STR_LIST = (False, 'string array')
    __FALSE_INT = (False, 'integer')
    __FALSE_DICT_LIST = (False, 'array or object')
    __FALSE_BOOL = (False, 'boolean')
    @staticmethod
    def STR_LIST(x):
        if not isinstance(x, list):
            return _VT.__FALSE_STR_LIST
        for i in x:
            if not (isinstance(i, str) or isinstance(i, unicode)):
                return _VT.__FALSE_STR_LIST
        return _VT.__TRUE_VAL
    @staticmethod
    def STR_REPEATABLE_EL(x):
        if isinstance(x, str) or isinstance(x, unicode):
            return _VT.__TRUE_VAL
        if not isinstance(x, list):
            return _VT.__FALSE_STR_REPEATABLE_EL
        for i in x:
            if not (isinstance(i, str) or isinstance(i, unicode)):
                return _VT.__FALSE_STR_REPEATABLE_EL
        return _VT.__TRUE_VAL
    @staticmethod
    def STR(x):
        return _VT.__TRUE_VAL if (isinstance(x, str) or isinstance(x, unicode)) else _VT.__FALSE_STR
    @staticmethod
    def LIST_OR_DICT(x):
        return _VT.__TRUE_VAL if (isinstance(x, list) or isinstance(x, dict)) else _VT.__FALSE_DICT_LIST
    @staticmethod
    def LIST(x):
        return _VT.__TRUE_VAL if (isinstance(x, list)) else _VT.__FALSE_LIST
    @staticmethod
    def DICT(x):
        return _VT.__TRUE_VAL if (isinstance(x, dict)) else _VT.__FALSE_DICT
    @staticmethod
    def BOOL(x):
        return _VT.__TRUE_VAL if (x is False or x is True) else _VT.__FALSE_BOOL
    @staticmethod
    def HREF(x):
        try:
            h = x.get('@href')
            if isinstance(h, str) or isinstance(h, unicode):
                return _VT.__TRUE_VAL
        except:
            pass
        return _VT.__FALSE_HREF
    @staticmethod
    def INT(x):
        return  _VT.__TRUE_VAL if (isinstance(x, int)) else _VT.__FALSE_INT
    @staticmethod
    def _extract_meta(x):
        try:
            return get_bf_meta_value(x)
        except:
            return None
    # meta forms
    @staticmethod
    def META_STR(x):
        return _VT.STR(_VT._extract_meta(x))
    @staticmethod
    def META_LIST(x):
        return _VT.LIST(_VT._extract_meta(x))
    @staticmethod
    def META_DICT(x):
        return _VT.DICT(_VT._extract_meta(x))
    @staticmethod
    def META_STR_LIST(x):
        return _VT.STR_LIST(_VT._extract_meta(x))
    @staticmethod
    def META_STR_REPEATABLE_EL(x):
        if not isinstance(x, list):
            x = [x]
        for el in x:
            vel = _VT._extract_meta(el)
            r = _VT.STR(vel)
            if r is not _VT.__TRUE_VAL:
                return _VT.__FALSE_STR_REPEATABLE_EL
        return _VT.__TRUE_VAL
    @staticmethod
    def META_HREF(x):
        return _VT.HREF(_VT._extract_meta(x))
    @staticmethod
    def META_BOOL(x):
        return _VT.BOOL(_VT._extract_meta(x))
    @staticmethod
    def META_INT(x):
        return _VT.INT(_VT._extract_meta(x))
    @staticmethod
    def convert2meta(v):
        if v is _VT.STR:
            return _VT.META_STR
        if v is _VT.LIST:
            return _VT.META_LIST
        if v is _VT.DICT:
            return _VT.META_DICT
        if v is _VT.STR_LIST:
            return _VT.META_STR_LIST
        if v is _VT.STR_REPEATABLE_EL:
            return _VT.META_STR_REPEATABLE_EL
        if v is _VT.INT:
            return _VT.META_INT
        if v is _VT.BOOL:
            return _VT.META_BOOL
        return v
_SchemaFragment._VT = _VT

_EMPTY_TUPLE = tuple()
_EMPTY_DICT = {}
####################################################################
# nexml element schema
_Req_NexmlEl_All = {'@id': _VT.STR,
                   }
_Exp_NexmlEl_Dir = {'otus': _VT.LIST,
                    'trees': _VT.LIST,
                   }
_Exp_NexmlEl_ByI = {'otusById': _VT.DICT, 
                    'treesById': _VT.DICT,
                    '^ot:otusElementOrder': _VT.STR_LIST,
                    '^ot:treesElementOrder': _VT.STR_LIST,
                   }
_All_NexmlEl_All = {'@about': _VT.STR,
                     '@generator': _VT.STR,
                     '@nexmljson': _VT.STR, # TODO: should be the purl. Move to xmlns?
                     '@version': _VT.STR,
                     '@xmlns': _VT.DICT,
                     '@nexml2json': _VT.STR,
                    }
_ExpMNexmlEl_All = {'ot:dataDeposit': _VT.HREF,
                    'ot:studyPublication': _VT.HREF,
                    'ot:studyPublicationReference': _VT.STR,
                    'ot:studyYear': _VT.INT,
                   }
_TypMNexmlEl_All = {'ot:curatorName': _VT.STR,
                    'ot:focalClade': _VT.INT,
                    'ot:focalCladeOTTTaxonName': _VT.STR,
                    'ot:notIntendedForSynthesis': _VT.BOOL,
                    'ot:notUsingRootedTrees': _VT.BOOL,
                    'ot:studyId': _VT.STR,
                    'ot:tag': _VT.STR_REPEATABLE_EL,
                    'ot:candidateTreeForSynthesis': _VT.STR_REPEATABLE_EL,
                   }

_v1_2_nexml = _SchemaFragment(required=_Req_NexmlEl_All,
                              expected=_Exp_NexmlEl_ByI,
                              allowed=_All_NexmlEl_All,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_ExpMNexmlEl_All,
                              type_checked_meta=_TypMNexmlEl_All,
                              using_hbf_meta=True)

_v1_0_nexml = _SchemaFragment(required=_Req_NexmlEl_All,
                              expected=_Exp_NexmlEl_Dir,
                              allowed=_All_NexmlEl_All,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_ExpMNexmlEl_All,
                              type_checked_meta=_TypMNexmlEl_All,
                              using_hbf_meta=True)

_v0_0_nexml = _SchemaFragment(required=_Req_NexmlEl_All,
                              expected=_Exp_NexmlEl_Dir,
                              allowed=_All_NexmlEl_All,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_ExpMNexmlEl_All,
                              type_checked_meta=_TypMNexmlEl_All,
                              using_hbf_meta=False)
#####################################################################

####################################################################
# otus element schema
_Req_OtusEl_ByI = {'otuById': _VT.DICT,
                  }
_Req_OtusEl_Dir = {'@id': _VT.STR,
                   'otu': _VT.DICT,
                  }

_v1_2_Otus = _SchemaFragment(required=_Req_OtusEl_ByI,
                              expected=_EMPTY_DICT,
                              allowed=_EMPTY_DICT,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=True)

_v1_0_Otus = _SchemaFragment(required=_Req_OtusEl_Dir,
                              expected=_EMPTY_DICT,
                              allowed=_EMPTY_DICT,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=True)

_v0_0_Otus = _SchemaFragment(required=_Req_OtusEl_Dir,
                              expected=_EMPTY_DICT,
                              allowed=_EMPTY_DICT,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=False)
#####################################################################
def _add_by_id_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    container._NexmlEl_Schema = _v1_2_nexml
    container._OtusEl_Schema = _v1_2_Otus

def _add_direct_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    container._NexmlEl_Schema = _v1_0_nexml
    container._OtusEl_Schema = _v1_0_Otus

def _add_badgerfish_nexson_schema_attributes(container):
    container._using_hbf_meta = False
    container._NexmlEl_Schema = _v0_0_nexml
    container._OtusEl_Schema = _v0_0_Otus
