#!/usr/bin/env python
from peyotl.nexson_syntax.helper import _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf

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
                 additional_allowed,
                 required_meta,
                 expected_meta,
                 using_hbf_meta):
        self.REQUIRED_2_VT = required
        self.EXPECETED_2_VT = expected
        self.ALLOWED_2_VT = additional_allowed
        self.REQUIRED_META_2_VT = required_meta
        self.EXPECTED_META_2_VT = expected_meta
        required_meta_keys = tuple(required_meta.keys())
        expected_meta_keys = tuple(expected_meta.keys())
        required_keys = tuple(required.keys())
        expected_keys = tuple(expected.keys())
        additional_allowed_keys = tuple(additional_allowed.keys())
        if using_hbf_meta:
            self.REQUIRED_META_KEY_SET = frozenset(['^' + i for i in required_meta_keys])
            self.EXPECTED_META_KEY_SET = frozenset(['^' + i for i in expected_meta_keys])
            self.REQUIRED_KEY_SET = frozenset(required_keys + tuple(self.REQUIRED_META_KEY_SET))
            self.EXPECETED_KEY_SET = frozenset(expected_keys + tuple(self.EXPECTED_META_KEY_SET))
            self.ALLOWED_KEY_SET = frozenset(tuple(self.REQUIRED_KEY_SET) 
                                              + tuple(self.EXPECETED_KEY_SET) 
                                              + additional_allowed_keys)
        else:
            self.REQUIRED_META_KEY_SET = frozenset(required_meta_keys)
            self.EXPECTED_META_KEY_SET = frozenset(expected_meta_keys)
            self.REQUIRED_KEY_SET = frozenset(required_keys)
            self.EXPECETED_KEY_SET = frozenset(expected_keys)
            self.ALLOWED_KEY_SET = frozenset(('meta', ) 
                                              + tuple(self.REQUIRED_KEY_SET) 
                                              + tuple(self.EXPECETED_KEY_SET) 
                                              + additional_allowed_keys)
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
    STR = 0
    LIST = 1
    DICT = 2
    STR_LIST = 3
    HREF = 4
    INT = 5


_EMPTY_TUPLE = tuple()
_EMPTY_DICT = {}
####################################################################
# nexml element schema
_NRequired_NexmlEl = {'@id': _VT.STR}
_NExpected_NexmlEl_Direct = {'otus': _VT.LIST,
                             'trees': _VT.LIST}
_NExpected_NexmlEl_ById = {'otusById': _VT.DICT, 
                           'treesById': _VT.DICT,
                           '^ot:otusElementOrder': _VT.STR_LIST,
                           '^ot:treesElementOrder': _VT.STR_LIST}
_NAllowed_NexmlEl = {'@about': _VT.STR,
                     '@generator': _VT.STR,
                     '@nexmljson': _VT.STR,
                     '@version': _VT.STR,
                     '@xmlns': _VT.DICT,
                     '@nexml2json': _VT.STR,}
_NExpectedMeta_NexmlEl_BF = {'ot:studyId': _VT.STR,
                             'ot:focalClade': _VT.INT,
                             'ot:studyPublication': _VT.HREF,
                             'ot:studyYear': _VT.INT,
                             'ot:curatorName': _VT.STR,
                             'ot:studyPublicationReference': _VT.STR,
                             'ot:dataDeposit': _VT.HREF
                            }


_by_id_nexml = _SchemaFragment(required=_NRequired_NexmlEl,
                        expected=_NExpected_NexmlEl_ById,
                        additional_allowed=_NAllowed_NexmlEl,
                        required_meta=_EMPTY_DICT,
                        expected_meta=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=True)

_direct_nexml = _SchemaFragment(required=_NRequired_NexmlEl,
                        expected=_NExpected_NexmlEl_Direct,
                        additional_allowed=_NAllowed_NexmlEl,
                        required_meta=_EMPTY_DICT,
                        expected_meta=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=True)

_bf_nexml = _SchemaFragment(required=_NRequired_NexmlEl,
                        expected=_NExpected_NexmlEl_Direct,
                        additional_allowed=_NAllowed_NexmlEl,
                        required_meta=_EMPTY_DICT,
                        expected_meta=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=False)
#####################################################################

def _add_by_id_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    container._NexmlEl_Schema = _by_id_nexml

def _add_direct_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    container._NexmlEl_Schema = _direct_nexml

def _add_badgerfish_nexson_schema_attributes(container):
    container._using_hbf_meta = False
    container._NexmlEl_Schema = _bf_nexml
