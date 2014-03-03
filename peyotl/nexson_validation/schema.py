#!/usr/bin/env python
def add_schema_attributes(container, nexson_version):
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
                 using_honeybadgerfish_meta):
        self.REQUIRED_KEYS = required_keys
        self.EXPECETED_KEYS = expected_keys
        self.PERMISSIBLE_KEYS = required_keys + expected_keys + additional_allowed_keys
        if using_honeybadgerfish_meta:
            self.REQUIRED_META_KEYS = tuple(['^' + i for i in required_meta_keys])
            self.EXPECTED_META_KEYS = tuple(['^' + i for i in expected_meta_keys])
        else:
            self.REQUIRED_META_KEYS = required_meta_keys
            self.EXPECTED_META_KEYS = expected_meta_keys
        self.USING_HBF_META = using_honeybadgerfish_meta



_NRequired_NexmlEl = ('@id', )
_NExpected_NexmlEl_Direct = ('@id', 'otus', 'trees',)
_NExpected_NexmlEl_ById = ('@id', 'otusById', 'treesById',)
_NAllowed_NexmlEl = ('@about', 
                     '@generator',
                     '@nexmljson',
                     '@version',
                     '@xmlns', )
_NExpectedMeta_NexmlEl_BF = ('ot:studyId', 
                             'ot:focalClade',
                             'ot:studyPublication',
                             'ot:studyYear',
                             'ot:curatorName', 
                             'ot:studyPublicationReference', 
                             'ot:dataDeposit',
                             'ot:tag')

def _add_by_id_nexson_schema_attributes(container):
    container._using_hbf_meta = True
    n = _SchemaFragment(required_keys=_NRequired_NexmlEl,
                        expected_keys=_NExpected_NexmlEl_ById,
                        additional_allowed_keys=_NAllowed_NexmlEl,
                        required_meta_keys=EMPTY_TUPLE,
                        expected_meta_keys=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=container._using_hbf_meta )
    container._NexmlEl_Schema = n

class DirectHBFValidationAdaptor(NexsonValidationAdaptor):
    container._using_hbf_meta = True
    n = _SchemaFragment(required_keys=_NRequired_NexmlEl,
                        expected_keys=_NExpected_NexmlEl_Direct,
                        additional_allowed_keys=_NAllowed_NexmlEl,
                        required_meta_keys=EMPTY_TUPLE,
                        expected_meta_keys=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=container._using_hbf_meta )
    container._NexmlEl_Schema = n

class BadgerFishValidationAdaptor(NexsonValidationAdaptor):
    container._using_hbf_meta = False
    n = _SchemaFragment(required_keys=_NRequired_NexmlEl,
                        expected_keys=_NExpected_NexmlEl_Direct,
                        additional_allowed_keys=_NAllowed_NexmlEl,
                        required_meta_keys=EMPTY_TUPLE,
                        expected_meta_keys=_NExpectedMeta_NexmlEl_BF,
                        using_hbf_meta=container._using_hbf_meta)
    container._NexmlEl_Schema = n
