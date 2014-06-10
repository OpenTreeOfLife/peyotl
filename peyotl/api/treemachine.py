#!/usr/bin/env python
from peyotl.api.wrapper import _WSWrapper, APIWrapper
import anyjson
from peyotl import get_logger
_LOG = get_logger(__name__)

class _TreemachineAPIWrapper(_WSWrapper):
    def __init__(self, domain):
        self._current_synth_info = None
        self._current_synth_id = None
        self.prefix = None
        self._raw_urls = False #TODO: should be config-dependent...
        _WSWrapper.__init__(self, domain)
        self.set_domain(domain)
    def set_domain(self, d):
        self._current_synth_info = None
        self._current_synth_id = None
        self._domain = d
        if self._raw_urls:
            self.prefix = '{d}/treemachine/ext/GoLS/graphdb'.format(d=d)
        else:
            self.prefix = '{d}/treemachine/v1'.format(d=d)
    domain = property(_WSWrapper.get_domain, set_domain)
    def get_current_synth_tree_id(self):
        if self._current_synth_info is None:
            self._current_synth_info = self.get_synthetic_tree_info()
            self._current_synth_id = self._current_synth_info['draftTreeName']
        return self._current_synth_id
    current_synth_tree_id = property(get_current_synth_tree_id)
    def get_synthetic_tree_info(self):
        uri = '{p}/getDraftTreeID'.format(p=self.prefix)
        return self.json_http_post(uri)
    def get_synthetic_tree_id_list(self):
        uri = '{p}/getSourceTreeIDs'.format(p=self.prefix)
        return self.json_http_post(uri)
    def get_synthetic_source_list(self):
        uri = '{p}/getSynthesisSourceList'.format(p=self.prefix)
        return self.json_http_post(uri)
    def get_source_tree(self, tree_id=None, format='newick', node_id=None, max_depth=None):
        uri = '{p}/getSourceTree'.format(p=self.prefix)
        return self._get_tree(uri, tree_id, format=format, node_id=node_id, max_depth=max_depth)
    def get_synthetic_tree(self, tree_id=None, format='newick', node_id=None, max_depth=None):
        uri = '{p}/getSyntheticTree'.format(p=self.prefix)
        return self._get_tree(uri, tree_id=tree_id, format=format, node_id=node_id, max_depth=max_depth)
    def get_synth_tree_pruned(self, tree_id=None, node_ids=None, ott_ids=None):
        if (tree_id is not None) and (tree_id != self.current_synth_tree_id):
            #TODO getDraftTreeSubtreeForNodes should take a treeID arg
            raise NotImplementedError("Treemachine's getDraftTreeSubtreeForNodes does not take a tree ID yet")
        data = {}
        if node_ids:
            data['nodeIds'] = node_ids
        if ott_ids:
            data['ottIds'] = ott_ids
        if not data:
            raise ValueError('Either "node_ids" or "ott_ids" must be supplied')
        uri = '{p}/getDraftTreeSubtreeForNodes'.format(p=self.prefix)
        return self.json_http_post(uri, data=anyjson.dumps(data))
    def _get_tree(self, uri, tree_id, format='newick', node_id=None, max_depth=None):
        if tree_id is None:
            tree_id = self.current_synth_tree_id
        format_list = ['newick', 'arguson']
        if format.lower() not in format_list:
            raise ValueError('Tree "format" must be a value in {}'.format(repr(format_list)))
        data = {'treeID': tree_id,
                'format': format}
        if node_id is not None:
            data['subtreeNodeID'] = str(node_id)
        if max_depth is not None:
            data['maxDepth'] = max_depth
        return self.json_http_post(uri, data=anyjson.dumps(data))
    def get_node_id_for_ott_id(self, ott_id):
        uri = '{p}/getNodeIDForottId'.format(p=self.prefix)
        data = {'ottId': str(ott_id)}
        return self.json_http_post(uri, data=anyjson.dumps(data))

def Treemachine(domains=None):
    return APIWrapper(domains=domains).treemachine