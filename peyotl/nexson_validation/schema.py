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
                 required_keys,
                 expected_keys,
                 additional_allowed_keys,
                 required_meta_keys,
                 expected_meta_keys,
                 using_hbf_meta):
        if using_hbf_meta:
            self.REQUIRED_META_KEYS = frozenset(['^' + i for i in required_meta_keys])
            self.EXPECTED_META_KEYS = frozenset(['^' + i for i in expected_meta_keys])
            self.REQUIRED_KEYS = frozenset(required_keys + tuple(self.REQUIRED_META_KEYS))
            self.EXPECETED_KEYS = frozenset(expected_keys + tuple(self.EXPECTED_META_KEYS))
            self.PERMISSIBLE_KEYS = frozenset(tuple(self.REQUIRED_KEYS) 
                                              + tuple(self.EXPECETED_KEYS) 
                                              + additional_allowed_keys)
        else:
            self.REQUIRED_META_KEYS = frozenset(required_meta_keys)
            self.EXPECTED_META_KEYS = frozenset(expected_meta_keys)
            self.REQUIRED_KEYS = frozenset(required_keys)
            self.EXPECETED_KEYS = frozenset(expected_keys)
            self.PERMISSIBLE_KEYS = frozenset(('meta', ) 
                                              + tuple(self.REQUIRED_KEYS) 
                                              + tuple(self.EXPECETED_KEYS) 
                                              + additional_allowed_keys)
        self.USING_HBF_META = using_hbf_meta



_EMPTY_TUPLE = tuple()
_NRequired_NexmlEl = ('@id', )
_NExpected_NexmlEl_Direct = ('otus', 'trees',)
_NExpected_NexmlEl_ById = ('otusById', 
                           'treesById',
                           '^ot:otusElementOrder', 
                           '^ot:treesElementOrder')
_NAllowed_NexmlEl = ('@about', 
                     '@generator',
                     '@nexmljson',
                     '@version',
                     '@xmlns', 
                     '@nexml2json')
_NExpectedMeta_NexmlEl_BF = ('ot:studyId', 
                             'ot:focalClade',
                             'ot:studyPublication',
                             'ot:studyYear',
                             'ot:curatorName', 
                             'ot:studyPublicationReference', 
                             'ot:dataDeposit',)


def _add_by_id_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    n = _SchemaFragment(required_keys=_NRequired_NexmlEl,
                        expected_keys=_NExpected_NexmlEl_ById,
                        additional_allowed_keys=_NAllowed_NexmlEl,
                        required_meta_keys=_EMPTY_TUPLE,
                        expected_meta_keys=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=container._using_hbf_meta )
    container._NexmlEl_Schema = n

def _add_direct_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    n = _SchemaFragment(required_keys=_NRequired_NexmlEl,
                        expected_keys=_NExpected_NexmlEl_Direct,
                        additional_allowed_keys=_NAllowed_NexmlEl,
                        required_meta_keys=_EMPTY_TUPLE,
                        expected_meta_keys=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=container._using_hbf_meta )
    container._NexmlEl_Schema = n

def _add_badgerfish_nexson_schema_attributes(container):
    container._using_hbf_meta = False
    n = _SchemaFragment(required_keys=_NRequired_NexmlEl,
                        expected_keys=_NExpected_NexmlEl_Direct,
                        additional_allowed_keys=_NAllowed_NexmlEl,
                        required_meta_keys=_EMPTY_TUPLE,
                        expected_meta_keys=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=container._using_hbf_meta)
    container._NexmlEl_Schema = n
