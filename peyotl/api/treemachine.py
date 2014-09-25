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
        self.use_v1 = False
        _WSWrapper.__init__(self, domain)
        self.set_domain(domain)
    def set_domain(self, d):
        self._current_synth_info = None
        self._current_synth_id = None
        self._domain = d
        if self._raw_urls:
            self.prefix = '{d}/treemachine/ext/GoLS/graphdb'.format(d=d)
        elif self.use_v1:
            self.prefix = '{d}/treemachine/v1'.format(d=d)
        else:
            self.prefix = '{d}/v2/tree_of_life'.format(d=d)
            self.graph_prefix = '{d}/v2/graph'.format(d=d)
    domain = property(_WSWrapper.get_domain, set_domain)
    def get_current_synth_tree_id(self):
        if self._current_synth_info is None:
            self._current_synth_info = self.get_synthetic_tree_info()
            if self.use_v1:
                self._current_synth_id = self._current_synth_info['draftTreeName']
            else:
                self._current_synth_id = self._current_synth_info['tree_id']
        return self._current_synth_id
    current_synth_tree_id = property(get_current_synth_tree_id)
    def get_synthetic_tree_info(self):
        if self.use_v1:
            uri = '{p}/getDraftTreeID'.format(p=self.prefix)
        else:
            uri = '{p}/about'.format(p=self.prefix)
        return self.json_http_post_raise(uri)
    def get_synthetic_tree_id_list(self):
        if self.use_v1:
            uri = '{p}/getSourceTreeIDs'.format(p=self.prefix)
            return self.json_http_post_raise(uri)
        r = self.get_synthetic_tree_info()
        raw_study_list = r['study_list']
        return raw_study_list

    def get_synthetic_source_list(self):
        uri = '{p}/getSynthesisSourceList'.format(p=self.prefix)
        return self.json_http_post_raise(uri)
    def get_source_tree(self, tree_id=None, format='newick', node_id=None, max_depth=None, **kwargs):
        if self.use_v1:
            uri = '{p}/getSourceTree'.format(p=self.prefix)
            return self._get_tree(uri, tree_id, format=format, node_id=node_id, max_depth=max_depth)
        else:
            uri = '{p}/source_tree'.format(p=self.graph_prefix)
            study_id = kwargs.get('study_id', '') # should not be kwarg #TODO
            if len(study_id) < 3 or study_id[2] != '_':
                study_id = 'pg_' + study_id
            data = {'git_sha': kwargs.get('git_sha', ''),
                    'study_id': study_id,
                    'tree_id': tree_id}
            return self.json_http_post_raise(uri, data=anyjson.dumps(data))
    def get_synthetic_tree(self, tree_id=None, format='newick', node_id=None, max_depth=None, ott_id=None):
        if self.use_v1:
            uri = '{p}/getSyntheticTree'.format(p=self.prefix)
        else:
            uri = '{p}/subtree'.format(p=self.prefix)
        return self._get_tree(uri,
                              tree_id=tree_id,
                              format=format,
                              node_id=node_id,
                              max_depth=max_depth,
                              ott_id=ott_id)
    def node_info(self, node_id=None, ott_id=None, include_lineage=False):
        if self.use_v1:
            raise NotImplemented('node_info was added in v2 of the API')
        uri = '{p}/node_info'.format(p=self.graph_prefix)
        data = {'include_lineage': bool(include_lineage)}
        if node_id and ott_id:
            raise ValueError('You can only specify one of node_id or ott_id')
        if not node_id and not ott_id:
            raise ValueError('You must specify one of node_id or ott_id')
        if node_id:
            data['node_id'] = int(node_id)
        else:
            data['ott_id'] = int(ott_id)
        return self.json_http_post_raise(uri, data=anyjson.dumps(data))

    def mrca(self, ott_ids=None, node_ids=None):
        if not (ott_ids or node_ids):
            raise ValueError('ott_ids or node_ids must be specified')
        assert not self.use_v1
        uri = '{p}/mrca'.format(p=self.prefix)
        data = {'ott_ids':ott_ids, 'node_ids': node_ids}
        return self.json_http_post_raise(uri, data=anyjson.dumps(data))
    def get_synth_tree_pruned(self, tree_id=None, node_ids=None, ott_ids=None):
        if (tree_id is not None) and (tree_id != self.current_synth_tree_id):
            #TODO getDraftTreeSubtreeForNodes should take a treeID arg
            raise NotImplementedError("Treemachine's getDraftTreeSubtreeForNodes does not take a tree ID yet")
        data = {}
        if self.use_v1:
            if node_ids:
                data['nodeIds'] = node_ids
            if ott_ids:
                data['ottIds'] = ott_ids
        else:
            if node_ids:
                data['node_ids'] = node_ids
            if ott_ids:
                data['ott_ids'] = ott_ids

        if not data:
            raise ValueError('Either "node_ids" or "ott_ids" must be supplied')
        if self.use_v1:
            uri = '{p}/getDraftTreeSubtreeForNodes'.format(p=self.prefix)
        else:
            uri = '{p}/induced_subtree'.format(p=self.prefix)
        return self.json_http_post_raise(uri, data=anyjson.dumps(data))
    induced_subtree = get_synth_tree_pruned
    def _get_tree(self, uri, tree_id, format='newick', node_id=None, max_depth=None, ott_id=None):
        if tree_id is None:
            tree_id = self.current_synth_tree_id
        if node_id is None and ott_id is None:
            raise ValueError('"node_id" or "ott_id" must be specified')
        format_list = ['newick', 'arguson']
        if format.lower() not in format_list:
            raise ValueError('Tree "format" must be a value in {}'.format(repr(format_list)))
        if self.use_v1:
            data = {'treeID': tree_id,
                    'format': format}
            if node_id is not None:
                data['subtreeNodeID'] = str(node_id)
            if max_depth is not None:
                data['maxDepth'] = max_depth
        else:
            data = {'tree_id': tree_id,}
            if node_id is not None:
                data['node_id'] = str(node_id)
            else:
                if ott_id is None:
                    return ValueError('ott_id or node_id must be specified')
                data['ott_id'] = ott_id
        return self.json_http_post_raise(uri, data=anyjson.dumps(data))
    def get_node_id_for_ott_id(self, ott_id):
        uri = '{p}/getNodeIDForottId'.format(p=self.prefix)
        data = {'ottId': str(ott_id)}
        return self.json_http_post_raise(uri, data=anyjson.dumps(data))

def Treemachine(domains=None, **kwargs):
    return APIWrapper(domains=domains, **kwargs).treemachine
