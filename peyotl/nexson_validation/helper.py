#!/usr/bin/env

class SeverityCodes(object):
    '''An enum of Warning/Error severity
    '''
    ERROR, WARNING = range(2)
    facets = ['ERROR', 'WARNING']
    numeric_codes_registered = set(range(len(facets)))
