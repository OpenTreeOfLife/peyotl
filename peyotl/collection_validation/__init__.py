#!/usr/bin/env python
'''Functions for validating collection JSON.
'''
from peyotl.nexson_syntax.helper import NexsonError
#from peyotl.collection_validation.warning_codes import CollectionWarningCodes
#from peyotl.collection_validation.logger import CollectionValidationLogger
from peyotl.collection_validation.adaptor import create_validation_adaptor

def validate_collection(obj, retain_deprecated=True, **kwargs):
    '''Takes an `obj` that is a collection object.
    `retain_deprecated` if False, then `obj` may be modified to replace
        deprecated constructs with new syntax. If it is True, the `obj` will
        not be modified.
    Returns the pair:
        validatation_log, adaptor
    `validatation_log` will be an instance of type collection_validation.logger.CollectionRichLogger
        it will hold warning and error messages.
    `adaptor` will be an instance of collection_validation.nexson_adaptor.CollectionValidationAdaptor [TODO]
        it holds a reference to `obj` and the bookkeepping data necessary to attach
        the log message to `obj` if
    '''
    #v = CollectionValidationLogger(store_messages=True)
    #v.retain_deprecated = retain_deprecated
    # Gather and report errors in a simple list
    errors = [ ]
    n = create_validation_adaptor(obj, errors, **kwargs)
    return errors, n

