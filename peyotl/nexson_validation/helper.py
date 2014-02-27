#!/usr/bin/env
VERSION = '0.0.3a'
class NexsonError(Exception):
    def __init__(self, v):
        self.value = v
    def __str__(self):
        return repr(self.v)

class SeverityCodes(object):
    '''An enum of Warning/Error severity
    '''
    ERROR, WARNING = range(2)
    facets = ['ERROR', 'WARNING']
    numeric_codes_registered = set(range(len(facets)))
