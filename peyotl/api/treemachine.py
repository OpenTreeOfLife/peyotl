#!/usr/bin/env python
from peyotl.utility import get_config_object, get_logger
from peyotl.api.wrapper import _WSWrapper, APIWrapper
from peyotl.api.study_ref import StudyRef
from peyotl.api.taxon import TaxonWrapper, TaxonHolder
import anyjson
_LOG = get_logger(__name__)
_EMPTY_TUPLE = tuple()
def _treemachine_tax_source2dict(tax_source):
    d = {}
    tax_source = tax_source.strip()
    if not tax_source:
        return d
    r = [i.strip() for i in tax_source.split(',')]
    for el in r:
        k, v = el.split(':')
        d[k] = v
    return d

class GoLNode(TaxonHolder):
    def __init__(self,
                 prop_dict,
                 treemachine_wrapper=None,
                 graph_of_life=None,
                 taxon=None,
                 nearest_taxon=None,
                 node_id=None):
        self._treemachine_wrapper = treemachine_wrapper
        self._graph_of_life = graph_of_life
        if node_id is None:
            self._node_id = prop_dict['mrca_node_id']
        else:
            self._node_id = node_id
        if taxon is None:
            oi = prop_dict.get('ott_id')
            if oi == 'null':
                oi = None
            if oi is not None:
                taxon_dict = {'ot:ottId': oi,
                              'rank': prop_dict.get('mrca_rank'),
                              'ot:ottTaxonName': prop_dict.get('mrca_name'),
                              'unique_name': prop_dict.get('mrca_unique_name'),
                              'treemachine_node_id': self.node_id
                             }
                #TODO should write wrappers for getting the taxomachine wrapper from treemachine wrapper...
                taxon = TaxonWrapper(prop_dict=taxon_dict)
            if nearest_taxon is None:
                taxon_dict = {'ot:ottId': prop_dict['nearest_taxon_mrca_ott_id'],
                              'rank': prop_dict.get('nearest_taxon_mrca_rank'),
                              'ot:ottTaxonName': prop_dict.get('nearest_taxon_mrca_name'),
                              'unique_name': prop_dict.get('nearest_taxon_mrca_unique_name'),
                              'treemachine_node_id': prop_dict.get('nearest_taxon_mrca_node_id')
                             }
                assert prop_dict['nearest_taxon_mrca_ott_id'] != 'null'
                #TODO should write wrappers for getting the taxomachine wrapper from treemachine wrapper...
                self._nearest_taxon = TaxonWrapper(prop_dict=taxon_dict)
            else:
                self._nearest_taxon = nearest_taxon
        TaxonHolder.__init__(self, taxon)
        if self._taxon is not None:
            assert (nearest_taxon is None) or (nearest_taxon is self._taxon)
            self._nearest_taxon = self._taxon

        self._subtree_newick = None
        self._synth_sources = prop_dict.get('synth_sources')
        self._in_synth_tree = prop_dict.get('in_synth_tree')
        self._tax_source = prop_dict.get('tax_source')
        self._in_graph = prop_dict.get('in_graph')
        self._num_tips = prop_dict.get('num_tips')
        self._num_synth_children = prop_dict.get('num_synth_children')
    @property
    def node_info_fetched(self):
        return not self._in_graph is None
    def fetch_node_info(self):
        prop_dict = self._treemachine_wrapper.node_info(node_id=self.node_id)
        self._synth_sources = [StudyRef(i) for i in prop_dict.get('synth_sources', [])]
        self._in_synth_tree = prop_dict.get('in_synth_tree')
        self._tax_source = _treemachine_tax_source2dict(prop_dict.get('tax_source', ''))
        self._in_graph = bool(prop_dict.get('in_graph'))
        self._num_tips = prop_dict.get('num_tips')
        self._num_synth_children = prop_dict.get('num_synth_children')
        if prop_dict['ott_id'] not in [None, 'null']:
            assert prop_dict['ott_id'] == self.ott_id
            assert prop_dict['ott_id'] == self.ott_id
            assert prop_dict['rank'] == self.rank
        assert prop_dict['node_id'] == self.node_id
    @property
    def synth_sources(self):
        if not self.node_info_fetched:
            self.fetch_node_info()
        return self._synth_sources
    @property
    def in_synth_tree(self):
        if not self.node_info_fetched:
            self.fetch_node_info()
        return self._in_synth_tree
    @property
    def tax_source(self):
        if not self.node_info_fetched:
            self.fetch_node_info()
        return self._tax_source
    @property
    def in_graph(self):
        if not self.node_info_fetched:
            self.fetch_node_info()
        return self._in_graph
    @property
    def num_tips(self):
        if not self.node_info_fetched:
            self.fetch_node_info()
        return self._num_tips
    @property
    def num_synth_children(self):
        if not self.node_info_fetched:
            self.fetch_node_info()
        return self._num_synth_children

    @property
    def subtree_newick(self):
        if self._subtree_newick is None:
            r = self._treemachine_wrapper.get_synthetic_tree(node_id=self.node_id)
            if self._graph_of_life:
                assert r['tree_id'] == self._graph_of_life['tree_id']
            self._subtree_newick = r['newick']
        return self._subtree_newick
    @property
    def node_id(self):
        return self._node_id
    @property
    def nearest_taxon(self):
        return self._nearest_taxon
    def write_report(self, output):
        self._taxon.write_report(output)
    @property
    def is_taxon(self):
        return self._taxon is not None
    @property
    def treemachine_node_id(self):
        return self._node_id

class MRCAGoLNode(GoLNode):
    def __init__(self, prop_dict, treemachine_wrapper=None, graph_of_life=None):
        GoLNode.__init__(self, prop_dict, treemachine_wrapper=treemachine_wrapper, graph_of_life=graph_of_life)
        x = prop_dict.get('invalid_node_ids')
        self._invalid_node_ids = tuple(x) if x else _EMPTY_TUPLE
        x = prop_dict.get('invalid_ott_ids')
        self._invalid_ott_ids = tuple(x) if x else _EMPTY_TUPLE
        x = prop_dict.get('node_ids_not_in_tree')
        self._node_ids_not_in_tree = tuple(x) if x else _EMPTY_TUPLE
        x = prop_dict.get('ott_ids_not_in_tree')
        self._ott_ids_not_in_tree = tuple(x) if x else _EMPTY_TUPLE
    @property
    def invalid_node_ids(self):
        return self._invalid_node_ids
    @property
    def invalid_ott_ids(self):
        return self._invalid_ott_ids
    @property
    def node_ids_not_in_tree(self):
        return self._node_ids_not_in_tree
    @property
    def ott_ids_not_in_tree(self):
        return self._ott_ids_not_in_tree


class _TreemachineAPIWrapper(_WSWrapper):
    def __init__(self, domain, **kwargs):
        self._config = kwargs.get('config')
        if self._config is None:
            self._config = get_config_object()
        self._current_synth_info = None
        self._current_synth_id = None
        self.prefix = None
        r = self._config.get_from_config_setting_cascade([('apis', 'treemachine_raw_urls'),
                                                          ('apis', 'raw_urls')],
                                                         "FALSE")
        self._raw_urls = (r.lower() == 'true')
        self._api_vers = self._config.get_from_config_setting_cascade([('apis', 'treemachine_api_version'),
                                                                       ('apis', 'api_version')],
                                                                      "2")
        self.use_v1 = (self._api_vers == "1")
        _WSWrapper.__init__(self, domain, **kwargs)
        self.domain = domain
    @property
    def domain(self):
        return self._domain
    @domain.setter
    def domain(self, d): #pylint: disable=W0221
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
    @property
    def current_synth_tree_id(self):
        if self._current_synth_info is None:
            self._current_synth_info = self.synthetic_tree_info
            if self.use_v1:
                self._current_synth_id = self._current_synth_info['draftTreeName']
            else:
                self._current_synth_id = self._current_synth_info['tree_id']
        return self._current_synth_id
    @property
    def synthetic_tree_info(self):
        if self.use_v1:
            uri = '{p}/getDraftTreeID'.format(p=self.prefix)
        else:
            uri = '{p}/about'.format(p=self.prefix)
        return self.json_http_post_raise(uri)
    @property
    def synthetic_tree_id_list(self):
        if self.use_v1:
            uri = '{p}/getSourceTreeIDs'.format(p=self.prefix)
            return self.json_http_post_raise(uri)
        r = self.synthetic_tree_info
        raw_study_list = r['study_list']
        return raw_study_list
    @property
    def synthetic_source_list(self):
        uri = '{p}/getSynthesisSourceList'.format(p=self.prefix)
        return self.json_http_post_raise(uri)
    # deprecated due to https://github.com/OpenTreeOfLife/treemachine/issues/170
    # format is redefined to match API
    #pylint: disable=W0622
    #def get_source_tree(self, tree_id=None, format='newick', node_id=None, max_depth=None, **kwargs):
    #    if self.use_v1:
    #        uri = '{p}/getSourceTree'.format(p=self.prefix)
    #        return self._get_tree(uri, tree_id, format=format, node_id=node_id, max_depth=max_depth)
    #    else:
    #        uri = '{p}/source_tree'.format(p=self.graph_prefix)
    #        study_id = kwargs.get('study_id', '')
    #        if len(study_id) < 3 or study_id[2] != '_':
    #            study_id = 'pg_' + study_id
    #        data = {'git_sha': kwargs.get('git_sha', ''),
    #                'study_id': study_id,
    #                'tree_id': tree_id}
    #        return self.json_http_post_raise(uri, data=anyjson.dumps(data))
    def get_synthetic_tree(self, tree_id=None, format='newick', node_id=None, max_depth=None, ott_id=None): #pylint: disable=W0622
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
            raise NotImplementedError('node_info was added in v2 of the API')
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

    def mrca(self, ott_ids=None, node_ids=None, wrap_response=False):
        if not (ott_ids or node_ids):
            raise ValueError('ott_ids or node_ids must be specified')
        assert not self.use_v1
        uri = '{p}/mrca'.format(p=self.prefix)
        data = {'ott_ids':ott_ids, 'node_ids': node_ids}
        resp = self.json_http_post_raise(uri, data=anyjson.dumps(data))
        if wrap_response:
            return MRCAGoLNode(resp, treemachine_wrapper=self)
        return resp
    def get_synth_tree_pruned(self, tree_id=None, node_ids=None, ott_ids=None):
        if (tree_id is not None) and (tree_id != self.current_synth_tree_id):
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
    def _get_tree(self, uri, tree_id, format='newick', node_id=None, max_depth=None, ott_id=None): #pylint: disable=W0622
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
