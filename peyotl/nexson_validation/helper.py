#!/usr/bin/env
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

def errorReturn(msg):
    _LOG.debug(msg)
    return False

VERSION = '0.0.3a'
class NexsonError(Exception):
    def __init__(self, v):
        self.value = v
    def __str__(self):
        return repr(self.value)

class SeverityCodes(object):
    '''An enum of Warning/Error severity
    '''
    ERROR, WARNING = range(2)
    facets = ['ERROR', 'WARNING']
    numeric_codes_registered = set(range(len(facets)))

class _NEXEL:
    TOP_LEVEL = 0
    NEXML = 1
    OTUS = 2
    OTU = 3
    TREES = 4
    TREE = 5
    NODE = 6
    EDGE = 7
    META = 8
    INTERNAL_NODE = 9
    LEAF_NODE = 10
    CODE_TO_STR = {}
    CODE_TO_PAR_CODE = {}
    CODE_TO_OTHER_ID_KEY = {}
    CODE_TO_TOP_ENTITY_NAME = {}

_NEXEL.CODE_TO_STR = {
    _NEXEL.TOP_LEVEL: 'top-level',
    _NEXEL.NEXML: 'nexml',
    _NEXEL.OTUS: 'otus',
    _NEXEL.OTU: 'otu',
    _NEXEL.TREES: 'trees',
    _NEXEL.TREE: 'tree',
    _NEXEL.NODE: 'node',
    _NEXEL.INTERNAL_NODE: 'node',
    _NEXEL.LEAF_NODE: 'node',
    _NEXEL.EDGE: 'edge',
    _NEXEL.META: 'meta',
    None: 'unknown',
}
_NEXEL.CODE_TO_PAR_CODE = {
    _NEXEL.TOP_LEVEL: None,
    _NEXEL.NEXML: _NEXEL.TOP_LEVEL,
    _NEXEL.OTUS: _NEXEL.NEXML,
    _NEXEL.OTU: _NEXEL.OTUS,
    _NEXEL.TREES: _NEXEL.NEXML,
    _NEXEL.TREE: _NEXEL.TREES,
    _NEXEL.NODE: _NEXEL.TREE,
    _NEXEL.INTERNAL_NODE: _NEXEL.TREE,
    _NEXEL.LEAF_NODE: _NEXEL.TREE,
    _NEXEL.EDGE: _NEXEL.TREE,
    None: None,
}
_NEXEL.CODE_TO_OTHER_ID_KEY = {
    _NEXEL.TOP_LEVEL: None,
    _NEXEL.NEXML: None,
    _NEXEL.OTUS: '@otusID',
    _NEXEL.OTU: '@otuID',
    _NEXEL.TREES: '@treesID',
    _NEXEL.TREE: '@treeID',
    _NEXEL.NODE: '@nodeID',
    _NEXEL.INTERNAL_NODE: '@nodeID',
    _NEXEL.LEAF_NODE: '@nodeID',
    _NEXEL.EDGE: '@edgeID',
    None: None,
}
_NEXEL.CODE_TO_TOP_ENTITY_NAME = {
    _NEXEL.TOP_LEVEL: '',
    _NEXEL.NEXML: 'nexml',
    _NEXEL.OTUS: 'otus',
    _NEXEL.OTU: 'otus',
    _NEXEL.TREES: 'trees',
    _NEXEL.TREE: 'trees',
    _NEXEL.NODE: 'trees',
    _NEXEL.INTERNAL_NODE: 'trees',
    _NEXEL.LEAF_NODE: 'trees',
    _NEXEL.EDGE: 'trees',
    None: '',
}
