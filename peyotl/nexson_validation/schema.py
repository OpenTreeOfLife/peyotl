#!/usr/bin/env python
from peyotl.nexson_syntax.helper import extract_meta, \
                                        _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf
from peyotl.utility import get_logger
_LOG = get_logger(__name__)
#pylint: disable=W0613,W0212
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
        self.K2VT = {}
        for k, v in required.items():
            self.K2VT[k] = _VT.m2RawCheck[v]
        for k, v in expected.items():
            self.K2VT[k] = _VT.m2RawCheck[v]
        for k, v in allowed.items():
            self.K2VT[k] = _VT.m2RawCheck[v]
        required_meta_keys = tuple(required_meta.keys())
        expected_meta_keys = tuple(expected_meta.keys())
        required_keys = tuple(required.keys())
        expected_keys = tuple(expected.keys())
        allowed_keys = tuple(allowed.keys())
        if using_hbf_meta:
            for k, v in required_meta.items():
                self.K2VT['^' + k] = _VT._2HBFCheck[v]
            for k, v in expected_meta.items():
                self.K2VT['^' + k] = _VT._2HBFCheck[v]
            for k, v in type_checked_meta.items():
                self.K2VT['^' + k] = _VT._2HBFCheck[v]
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
                self.K2VT[k] = _VT._2BFCheck[v]
            for k, v in expected_meta.items():
                self.K2VT[k] = _VT._2BFCheck[v]
            for k, v in type_checked_meta.items():
                self.K2VT[k] = _VT._2BFCheck[v]
            self.K2VT['meta'] = _VT.m2RawCheck[_VT.LIST_OR_DICT]
            self.REQUIRED_META_KEY_SET = frozenset(required_meta_keys)
            self.EXPECTED_META_KEY_SET = frozenset(expected_meta_keys)
            targ = required_meta_keys + expected_meta_keys + tuple(type_checked_meta.keys())
            self.ALLOWED_META_KEY_SET = frozenset(targ)
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


__TRUE_VAL = (True, None)
__FALSE_STR = (False, 'str')
__FALSE_HREF = (False, 'href')
__FALSE_LIST = (False, 'array')
__FALSE_DICT = (False, 'object')
__FALSE_STR_REPEATABLE_EL = (False, 'string or string array')
__FALSE_STR_LIST = (False, 'string array')
__FALSE_INT = (False, 'integer')
__FALSE_FLOAT = (False, 'float')
__FALSE_DICT_LIST = (False, 'array or object')
__FALSE_BOOL = (False, 'boolean')


def _check_id(x, obj, k, vc):
    try:
        nid = x.get('@id')
    except:
        return
    if nid is not None:
        vc.adaptor._check_meta_id(nid, x, k, obj, vc)

def check_raw_bool(x, obj, k, vc):
    return __TRUE_VAL if (x is False or x is True) else __FALSE_BOOL
def check_obj_meta_bool(x, obj, k, vc):
    mo = extract_meta(x)
    _check_id(x, obj, k, vc)
    return check_raw_bool(mo, obj, k, vc)
def check_hbf_meta_bool(x, obj, k, vc):
    if isinstance(x, dict):
        return check_obj_meta_bool(x, obj, k, vc)
    return __TRUE_VAL if (x is False or x is True) else __FALSE_BOOL
def check_raw_dict(x, obj, k, vc):
    return __TRUE_VAL if (isinstance(x, dict)) else __FALSE_DICT
def check_obj_meta_dict(x, obj, k, vc):
    mo = extract_meta(x)
    _check_id(x, obj, k, vc)
    return check_raw_dict(mo, obj, k, vc)
def check_hbf_meta_dict(x, obj, k, vc):
    if isinstance(x, dict):
        return __TRUE_VAL
def check_href(x, obj, k, vc):
    try:
        _check_id(x, obj, k, vc)
        h = x.get('@href')
        if isinstance(h, str) or isinstance(h, unicode):
            return __TRUE_VAL
    except:
        pass
    return __FALSE_HREF
def check_raw_int(x, obj, k, vc):
    return  __TRUE_VAL if (isinstance(x, int)) else __FALSE_INT
def check_obj_meta_int(x, obj, k, vc):
    mo = extract_meta(x)
    _check_id(x, obj, k, vc)
    return check_raw_int(mo, obj, k, vc)
def check_hbf_meta_int(x, obj, k, vc):
    if isinstance(x, dict):
        return check_obj_meta_int(x, obj, k, vc)
    return check_raw_int(x, obj, k, vc)
def check_raw_float(x, obj, k, vc):
    return  __TRUE_VAL if (isinstance(x, float)) else __FALSE_FLOAT
def check_obj_meta_float(x, obj, k, vc):
    mo = extract_meta(x)
    _check_id(x, obj, k, vc)
    return check_raw_float(mo, obj, k, vc)
def check_hbf_meta_float(x, obj, k, vc):
    if isinstance(x, dict):
        return check_obj_meta_float(x, obj, k, vc)
    return check_raw_float(x, obj, k, vc)
def check_raw_list(x, obj, k, vc):
    return __TRUE_VAL if (isinstance(x, list)) else __FALSE_LIST
def check_obj_meta_list(x, obj, k, vc):
    mo = extract_meta(x)
    _check_id(x, obj, k, vc)
    return check_raw_list(mo, obj, k, vc)
def check_hbf_meta_list(x, obj, k, vc):
    if isinstance(x, dict):
        return check_obj_meta_list(x, obj, k, vc)
    return check_raw_list(x, obj, k, vc)
def check_list_or_dict(x, obj, k, vc):
    return __TRUE_VAL if (isinstance(x, list) or isinstance(x, dict)) else __FALSE_DICT_LIST
def check_raw_str(x, obj, k, vc):
    return __TRUE_VAL if (isinstance(x, str) or isinstance(x, unicode)) else __FALSE_STR
def check_obj_meta_str(x, obj, k, vc):
    mo = extract_meta(x)
    _check_id(x, obj, k, vc)
    return check_raw_str(mo, obj, k, vc)
def check_hbf_meta_str(x, obj, k, vc):
    if isinstance(x, dict):
        return check_obj_meta_str(x, obj, k, vc)
    return check_raw_str(x, obj, k, vc)
def check_raw_str_list(x, obj, k, vc):
    if not isinstance(x, list):
        return __FALSE_STR_LIST
    for i in x:
        if not (isinstance(i, str) or isinstance(i, unicode)):
            return __FALSE_STR_LIST
    return __TRUE_VAL
def check_obj_meta_str_list(x, obj, k, vc):
    mo = extract_meta(x)
    _check_id(x, obj, k, vc)
    return check_raw_str_list(mo, obj, k, vc)
def check_hbf_meta_str_list(x, obj, k, vc):
    if isinstance(x, dict):
        return check_obj_meta_str_list(x, obj, k, vc)
    return check_raw_str_list(x, obj, k, vc)
def check_raw_str_repeatable(x, obj, k, vc):
    if isinstance(x, str) or isinstance(x, unicode):
        return __TRUE_VAL
    if not isinstance(x, list):
        return __FALSE_STR_REPEATABLE_EL
    for i in x:
        if not (isinstance(i, str) or isinstance(i, unicode)):
            return __FALSE_STR_REPEATABLE_EL
    return __TRUE_VAL
def check_obj_meta_str_repeatable(x, obj, k, vc):
    if not isinstance(x, list):
        x = [x]
    for el in x:
        r = check_obj_meta_str(el, obj, k, vc)
        if r is not __TRUE_VAL:
            return __FALSE_STR_REPEATABLE_EL
    return __TRUE_VAL
def check_hbf_meta_str_repeatable(x, obj, k, vc):
    if not isinstance(x, list):
        x = [x]
    for el in x:
        r = check_hbf_meta_str(el, obj, k, vc)
        if r is not __TRUE_VAL:
            return __FALSE_STR_REPEATABLE_EL
    return __TRUE_VAL

class _VT:
    '''Value type enum'''
    BOOL = 0
    DICT = 1
    HREF = 2
    INT = 3
    LIST = 4
    LIST_OR_DICT = 5
    STR = 6
    STR_LIST = 7
    STR_REPEATABLE_EL = 8
    FLOAT = 9

    m2RawCheck = {
        BOOL: check_raw_bool,
        DICT: check_raw_dict,
        HREF: check_href,
        INT: check_raw_int,
        FLOAT: check_raw_float,
        LIST: check_raw_list,
        LIST_OR_DICT: check_list_or_dict,
        STR: check_raw_str,
        STR_LIST: check_raw_str_list,
        STR_REPEATABLE_EL: check_raw_str_repeatable,
    }
    _2HBFCheck = {
        BOOL: check_hbf_meta_bool,
        DICT: check_hbf_meta_dict,
        HREF: check_href,
        INT: check_raw_int,
        FLOAT: check_raw_float,
        LIST: check_hbf_meta_list,
        LIST_OR_DICT: check_list_or_dict,
        STR: check_hbf_meta_str,
        STR_LIST: check_hbf_meta_str_list,
        STR_REPEATABLE_EL: check_hbf_meta_str_repeatable,
    }

    _2BFCheck = {
        BOOL: check_obj_meta_bool,
        DICT: check_obj_meta_dict,
        HREF: check_href,
        INT: check_obj_meta_int,
        FLOAT: check_obj_meta_float,
        LIST: check_hbf_meta_list,
        LIST_OR_DICT: check_list_or_dict,
        STR: check_obj_meta_str,
        STR_LIST: check_obj_meta_str_list,
        STR_REPEATABLE_EL: check_obj_meta_str_repeatable,
    }

_SchemaFragment._VT = _VT

_EMPTY_DICT = {}
####################################################################
# nexml element schema
_Req_NexmlEl_All = {'@id': _VT.STR,
                   }
_Exp_NexmlEl_Dir = {'otus': _VT.LIST_OR_DICT,
                    'trees': _VT.LIST_OR_DICT,
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
_TypMNexmlEl_All = {'ot:curatorName': _VT.STR_REPEATABLE_EL,
                    'ot:focalClade': _VT.INT,
                    'ot:focalCladeOTTTaxonName': _VT.STR,
                    'ot:notIntendedForSynthesis': _VT.BOOL,
                    'ot:notUsingRootedTrees': _VT.BOOL,
                    'ot:studyId': _VT.STR,
                    'ot:tag': _VT.STR_REPEATABLE_EL,
                    'ot:taxonLinkPrefixes': _VT.DICT,
                    'ot:candidateTreeForSynthesis': _VT.STR_REPEATABLE_EL,
                    'xhtml:license': _VT.HREF,
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
                   'otu': _VT.LIST,
                  }
_All_OtusEl_Dir = {'@about': _VT.STR,
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
                              allowed=_All_OtusEl_Dir,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=True)

_v0_0_Otus = _SchemaFragment(required=_Req_OtusEl_Dir,
                              expected=_EMPTY_DICT,
                              allowed=_All_OtusEl_Dir,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=False)

####################################################################
# otu element schema
_Req_OtuEl_ByI = _EMPTY_DICT
_Req_OtuEl_Dir = {'@id': _VT.STR,
                 }
_All_OtuEl_ByI = {'@label': _VT.STR,
                 }
_All_OtuEl_Dir = {'@about': _VT.STR,
                  '@label': _VT.STR,
                 }
_ReqMOtuEl_All = {'ot:originalLabel': _VT.STR,
                 }
_ExpMOtuEl_All = {'ot:ottId': _VT.INT,
                 }
_TypMOtuEl_All = {'ot:treebaseOTUId': _VT.STR,
                  'ot:ottTaxonName': _VT.STR,
                  'ot:taxonLink': _VT.DICT,
                  "skos:altLabel": _VT.LIST_OR_DICT,
                 }
_v1_2_Otu = _SchemaFragment(required=_Req_OtuEl_ByI,
                            expected=_EMPTY_DICT,
                            allowed=_All_OtuEl_ByI,
                            required_meta=_ReqMOtuEl_All,
                            expected_meta=_ExpMOtuEl_All,
                            type_checked_meta=_TypMOtuEl_All,
                            using_hbf_meta=True)
_v1_0_Otu = _SchemaFragment(required=_Req_OtuEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_OtuEl_Dir,
                            required_meta=_ReqMOtuEl_All,
                            expected_meta=_ExpMOtuEl_All,
                            type_checked_meta=_TypMOtuEl_All,
                            using_hbf_meta=True)

_v0_0_Otu = _SchemaFragment(required=_Req_OtuEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_OtuEl_Dir,
                            required_meta=_ReqMOtuEl_All,
                            expected_meta=_ExpMOtuEl_All,
                            type_checked_meta=_TypMOtuEl_All,
                            using_hbf_meta=False)
#####################################################################

####################################################################
# trees element schema
_Req_TreesEl_ByI = {'@otus': _VT.STR,
                    'treeById': _VT.DICT,
                    '^ot:treeElementOrder': _VT.STR_LIST,
                  }
_Req_TreesEl_Dir = {'@id': _VT.STR,
                    '@otus': _VT.STR,
                    'tree': _VT.LIST_OR_DICT,
                  }
_All_TreesEl_Dir = {'@about': _VT.STR,
                  }

_v1_2_Trees = _SchemaFragment(required=_Req_TreesEl_ByI,
                              expected=_EMPTY_DICT,
                              allowed=_EMPTY_DICT,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=True)

_v1_0_Trees = _SchemaFragment(required=_Req_TreesEl_Dir,
                              expected=_EMPTY_DICT,
                              allowed=_All_TreesEl_Dir,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=True)

_v0_0_Trees = _SchemaFragment(required=_Req_TreesEl_Dir,
                              expected=_EMPTY_DICT,
                              allowed=_All_TreesEl_Dir,
                              required_meta=_EMPTY_DICT,
                              expected_meta=_EMPTY_DICT,
                              type_checked_meta=_EMPTY_DICT,
                              using_hbf_meta=False)
#####################################################################

####################################################################
# tree element schema
_Req_TreeEl_ByI = {'edgeBySourceId': _VT.DICT,
                   'nodeById': _VT.DICT,
                  }
_Req_TreeEl_Dir = {'edge': _VT.LIST,
                   'node': _VT.LIST,
                   '@id': _VT.STR,
                  }
_Exp_TreeEl_All = {'@xsi:type': _VT.STR, # could be a choice...
                  }
_All_TreeEl_ByI = {'@label': _VT.STR,
                 }
_All_TreeEl_Dir = {'@about': _VT.STR,
                  '@label': _VT.STR,
                 }
_ReqMTreeEl_ByI = {'ot:rootNodeId': _VT.STR,
                 }
_ReqMTreeEl_Dir = _EMPTY_DICT
_ExpMTreeEl_All = {'ot:branchLengthTimeUnit': _VT.STR,
                   'ot:branchLengthMode': _VT.STR,
                   'ot:curatedType': _VT.STR,
                   'ot:inGroupClade': _VT.STR,
                   }
_TypMTreeEl_All = {'ot:specifiedRoot': _VT.STR,
                   'ot:tag': _VT.STR_REPEATABLE_EL,
                   'ot:unrootedTree': _VT.BOOL,
                   }
_v1_2_Tree = _SchemaFragment(required=_Req_TreeEl_ByI,
                            expected=_Exp_TreeEl_All,
                            allowed=_All_TreeEl_ByI,
                            required_meta=_ReqMTreeEl_ByI,
                            expected_meta=_ExpMTreeEl_All,
                            type_checked_meta=_TypMTreeEl_All,
                            using_hbf_meta=True)
_v1_0_Tree = _SchemaFragment(required=_Req_TreeEl_Dir,
                            expected=_Exp_TreeEl_All,
                            allowed=_All_TreesEl_Dir,
                            required_meta=_ReqMTreeEl_Dir,
                            expected_meta=_ExpMTreeEl_All,
                            type_checked_meta=_TypMTreeEl_All,
                            using_hbf_meta=True)

_v0_0_Tree = _SchemaFragment(required=_Req_TreeEl_Dir,
                            expected=_Exp_TreeEl_All,
                            allowed=_All_TreesEl_Dir,
                            required_meta=_ReqMTreeEl_Dir,
                            expected_meta=_ExpMTreeEl_All,
                            type_checked_meta=_TypMTreeEl_All,
                            using_hbf_meta=False)
#####################################################################

####################################################################
# leaf node element schema
_Req_LeafEl_ByI = {'@otu': _VT.STR,
                  }
_Req_LeafEl_Dir = {'@id': _VT.STR,
                   '@otu': _VT.STR, # could be a choice...
                  }
_All_LeafEl_Dir = {'@about': _VT.STR,
                  }
_ReqMLeafEl_Dir = {'ot:isLeaf': _VT.BOOL,
                  }
_v1_2_Leaf = _SchemaFragment(required=_Req_LeafEl_ByI,
                            expected=_EMPTY_DICT,
                            allowed=_EMPTY_DICT,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=True)
_v1_0_Leaf = _SchemaFragment(required=_Req_LeafEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_LeafEl_Dir,
                            required_meta=_ReqMLeafEl_Dir,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=True)
_v0_0_Leaf = _SchemaFragment(required=_Req_LeafEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_LeafEl_Dir,
                            required_meta=_ReqMLeafEl_Dir,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=False)
#####################################################################

####################################################################
# internal node element schema
_Req_IntNEl_ByI = _EMPTY_DICT
_Req_IntNEl_Dir = {'@id': _VT.STR,
                  }
_All_IntNEl_ByI = {'@root': _VT.BOOL,
                  }
_All_IntNEl_Dir = {'@about': _VT.STR,
                  '@root': _VT.BOOL,
                  }

_TypMIntNEl_Dir = {'ot:isLeaf': _VT.BOOL,
                  }
_v1_2_IntN = _SchemaFragment(required=_Req_IntNEl_ByI,
                            expected=_EMPTY_DICT,
                            allowed=_All_IntNEl_ByI,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=True)
_v1_0_IntN = _SchemaFragment(required=_Req_IntNEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_IntNEl_Dir,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_TypMIntNEl_Dir,
                            using_hbf_meta=True)
_v0_0_IntN = _SchemaFragment(required=_Req_IntNEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_IntNEl_Dir,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_TypMIntNEl_Dir,
                            using_hbf_meta=False)
#####################################################################

####################################################################
# node element schema
_Req_NodeEl_ByI = _EMPTY_DICT
_Req_NodeEl_Dir = {'@id': _VT.STR,
                  }
_All_NodeEl_ByI = {'@otu': _VT.STR,
                   '@root': _VT.BOOL,
                  }
_All_NodeEl_Dir = {'@about': _VT.STR,
                   '@otu': _VT.STR,
                   '@root': _VT.BOOL,
                  }
_TypMNodeEl_Dir = {'ot:isLeaf': _VT.BOOL,
                  }
_v1_2_Node = _SchemaFragment(required=_Req_NodeEl_ByI,
                            expected=_EMPTY_DICT,
                            allowed=_All_NodeEl_ByI,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=True)
_v1_0_Node = _SchemaFragment(required=_Req_NodeEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_NodeEl_Dir,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_TypMNodeEl_Dir,
                            using_hbf_meta=True)
_v0_0_Node = _SchemaFragment(required=_Req_NodeEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_NodeEl_Dir,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_TypMNodeEl_Dir,
                            using_hbf_meta=False)
#####################################################################

####################################################################
# edge element schema
_Req_EdgeEl_ByI = {'@target': _VT.STR,
                   '@source': _VT.STR,
                  }
_Req_EdgeEl_Dir = {'@target': _VT.STR,
                   '@id': _VT.STR,
                   '@source': _VT.STR,
                  }
_All_EdgeEl_ByI = {'@length': _VT.FLOAT,
                  }
_All_EdgeEl_Dir = {'@about': _VT.STR,
                   '@length': _VT.FLOAT,
                  }
_v1_2_Edge = _SchemaFragment(required=_Req_EdgeEl_ByI,
                            expected=_EMPTY_DICT,
                            allowed=_All_EdgeEl_ByI,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=True)
_v1_0_Edge = _SchemaFragment(required=_Req_EdgeEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_EdgeEl_Dir,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=True)
_v0_0_Edge = _SchemaFragment(required=_Req_EdgeEl_Dir,
                            expected=_EMPTY_DICT,
                            allowed=_All_EdgeEl_Dir,
                            required_meta=_EMPTY_DICT,
                            expected_meta=_EMPTY_DICT,
                            type_checked_meta=_EMPTY_DICT,
                            using_hbf_meta=False)
#####################################################################

def _add_by_id_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    container._NexmlEl_Schema = _v1_2_nexml
    container._OtusEl_Schema = _v1_2_Otus
    container._OtuEl_Schema = _v1_2_Otu
    container._TreesEl_Schema = _v1_2_Trees
    container._TreeEl_Schema = _v1_2_Tree
    container._LeafEl_Schema = _v1_2_Leaf
    container._IntNEl_Schema = _v1_2_IntN
    container._EdgeEl_Schema = _v1_2_Edge

def _add_direct_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    container._NexmlEl_Schema = _v1_0_nexml
    container._OtusEl_Schema = _v1_0_Otus
    container._OtuEl_Schema = _v1_0_Otu
    container._TreesEl_Schema = _v1_0_Trees
    container._TreeEl_Schema = _v1_0_Tree
    container._LeafEl_Schema = _v1_0_Leaf
    container._IntNEl_Schema = _v1_0_IntN
    container._NodeEl_Schema = _v1_0_Node
    container._EdgeEl_Schema = _v1_0_Edge

def _add_badgerfish_nexson_schema_attributes(container):
    container._using_hbf_meta = False
    container._NexmlEl_Schema = _v0_0_nexml
    container._OtusEl_Schema = _v0_0_Otus
    container._OtuEl_Schema = _v0_0_Otu
    container._TreesEl_Schema = _v0_0_Trees
    container._TreeEl_Schema = _v0_0_Tree
    container._LeafEl_Schema = _v0_0_Leaf
    container._IntNEl_Schema = _v0_0_IntN
    container._EdgeEl_Schema = _v0_0_Edge
    container._NodeEl_Schema = _v0_0_Node
    