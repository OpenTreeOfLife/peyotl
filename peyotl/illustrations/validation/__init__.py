#!/usr/bin/env python
'''Functions for validating illustration JSON.
'''
from peyotl.illustrations.validation.adaptor import create_validation_adaptor

def validate_illustration(obj, retain_deprecated=True, **kwargs):
    '''Takes an `obj` that is an illustration object.
    `retain_deprecated` if False, then `obj` may be modified to replace
        deprecated constructs with new syntax. If it is True, the `obj` will
        not be modified.
    Returns the pair:
        errors, adaptor
    `errors` is a simple list of error messages
    `adaptor` will be an instance of illustrations.validation.adaptor.illustrationValidationAdaptor
        it holds a reference to `obj` and the bookkeepping data necessary to attach
        the log message to `obj` if
    '''
    # Gather and report errors in a simple list
    errors = []
    n = create_validation_adaptor(obj, errors, **kwargs)
    return errors, n

