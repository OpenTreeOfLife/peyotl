#!/usr/bin/env
VERSION = '0.0.3a'

class SeverityCodes(object):
    '''An enum of Warning/Error severity
    '''
    ERROR, WARNING = range(2)
    facets = ['ERROR', 'WARNING']
    numeric_codes_registered = set(range(len(facets)))
