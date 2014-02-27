#!/usr/bin/env python
'''Functions for validating NexSON.
'''
from peyotl.nexson_validation.warning_codes import NexsonWarningCodes
from peyotl.nexson_validation.validation_logger import FilteringLogger, \
                                                ValidationLogger

def validate_nexson(obj, warning_codes_to_skip=None, retain_deprecated=True):
    '''Takes an `obj` that is a NexSON object. 
    `warning_codes_to_skip` is None or an iterable collection of integers
        that correspond to facets of NexsonWarningCodes. Warnings associated
        with any code in the list will be suppressed.
    `retain_deprecated` if False, then `obj` may be modified to replace 
        deprecated constructs with new syntax. If it is True, the `obj` will
        not be modified.
    Returns the pair:
        validatation_log, adaptor
    `validatation_log` will be an instance of type nexson_validation.validation_logger.DefaultRichLogger
        it will hold warning and error messages.
    `adaptor` will be an instance of nexson_validation.nexson_adaptor.NexsonValidationAdaptor
        it holds a reference to `obj` and the bookkeepping data necessary to attach
        the validation_log message to `obj` if 
    '''
    if warning_codes_to_skip:
        v = FilteringLogger(codes_to_skip=list(warning_codes_to_skip), store_messages=True)
    else:
        v = ValidationLogger(store_messages=True)
    v.retain_deprecated = retain_deprecated
    n = NexsonValidationAdaptor(obj, v)
    return v, n

