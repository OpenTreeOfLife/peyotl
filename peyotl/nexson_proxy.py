#!/usr/bin/env python
'''Provides high level wrappers around a Nexson data model blob to
let it be treated as if it were a list of OTUs and a list of trees

Accessors return either references to part of the NexSON or wrappers around
those entities (not copies!)

Weakrefs are used, so the more inclusive containers must be kept in scope
while you are accessing constituents.

Currently converts any NexSON blob to HBF v1.2 data model!
'''
from peyotl.nexson_syntax import BY_ID_HONEY_BADGERFISH, \
                                 convert_nexson_format, \
                                 detect_nexson_version, \
                                 get_nexml_el, \
                                 read_as_json
from peyotl.utility import get_logger
import weakref
_LOG = get_logger(__name__)
def otu_iter_nexson_proxy(nexson_proxy, otu_sort=None):
    '''otu_sort can be None (not sorted or stable), True (sorted by ID lexigraphically)
    or a key function for a sort function on list of otuIDs

    Note that if there are multiple OTU groups, the NexSON specifies the order of sorting
        of the groups (so the sort argument here only refers to the sorting of OTUs within
        a group)
    '''
    nexml_el = nexson_proxy._nexml_el
    og_order = nexml_el['^ot:otusElementOrder']
    ogd = nexml_el['otusById']
    for og_id in og_order:
        og = ogd[og_id]
        if otu_sort is None:
            for k, v in og:
                yield nexson_proxy._create_otu_proxy(k, v)
        else:
            key_list = list(og.keys())
            if otu_sort is True:
                key_list.sort()
            else:
                key_list.sort(key=otu_sort)
            for k in key_list:
                v = og[k]
                yield nexson_proxy._create_otu_proxy(k, v)

def tree_iter_nexson_proxy(nexson_proxy):
    '''Iterates over NexsonTreeProxy objects in order determined by the nexson blob'''
    nexml_el = nexson_proxy._nexml_el
    tg_order = nexml_el['^ot:treesElementOrder']
    tgd = nexml_el['treesById']
    for tg_id in tg_order:
        tg = tgd[tg_id]
        tree_order = tg['^ot:treeElementOrder']
        tbid = tg['treeById']
        otus = tg['@otus']
        for k in tree_order:
            v = tbid[k]
            yield nexson_proxy._create_tree_proxy(tree_id=k, tree=v, otus=otus)

def reverse_edge_by_source_dict(ebs, root_id):
    d = {}
    for edge_by_id in ebs.values():
        for edge_id, edge in edge_by_id.items():
            t = edge['@target']
            assert t not in d
            d[t] = (edge_id, edge)
    assert root_id in ebs
    assert root_id not in d
    d[root_id] = (None, None)
    return d
class NexsonProxy(object):
    class NexsonOTUProxy(object):
        def __init__(self, nexson_proxy, otu_id, otu):
            self._nexson_proxy = nexson_proxy
            self._otu_id = otu_id
            self._otu = otu
        @property
        def ott_id(self):
            return self._otu.get('^ot:ottId')
        @property
        def otu(self):
            return self._otu
        @property
        def _id(self):
            return self._otu_id
        def get(self, key, default=None):
            return self._otu.get(key, default)
        def keys(self, key, default=None):
            return self._otu.get(key, default)
    def __init__(self, filepath='', nexson=None):
        self.filepath = filepath
        if nexson is None:
            if not filepath:
                raise ValueError('Either a filepath or nexson argument must be provided')
            self._nexson = read_as_json(self.filepath)
        else:
            self._nexson = nexson
        v = detect_nexson_version(self._nexson)
        if v != BY_ID_HONEY_BADGERFISH:
            _LOG.debug('NexsonProxy converting to hbf1.2')
            convert_nexson_format(self._nexson, BY_ID_HONEY_BADGERFISH)
        self._nexml_el = get_nexml_el(self._nexson)
        self._otu_cache = {}
        self._tree_cache = {}
        self._wr = None
    def otu_iter(self):
        return iter(otu_iter_nexson_proxy(self))
    def tree_iter(self):
        return iter(tree_iter_nexson_proxy(self))
    def _create_otu_proxy(self, otu_id, otu):
        np = self._otu_cache.get(otu_id)
        if np is None:
            if self._wr is None:
                self._wr = weakref.proxy(self)
            np = NexsonProxy.NexsonOTUProxy(self._wr, otu_id, otu)
            self._otu_cache[otu_id] = np
        return np
    def _create_tree_proxy(self, tree_id, tree, otus):
        np = self._tree_cache.get(tree_id)
        if np is None:
            if self._wr is None:
                self._wr = weakref.proxy(self)
            np = NexsonTreeProxy(tree_id=tree_id, tree=tree, otus=otus, nexson_proxy=self._wr)
            self._tree_cache[tree_id] = np
        return np
    def get_tree(self, tree_id):
        np = self._tree_cache.get(tree_id)
        if np is not None:
            return np
        tgd = self._nexml_el['treesById']
        for tg in tgd.values():
            tbid = tg['treeById']
            if tree_id in tbid:
                otus = tg['@otus']
                tree = tbid[tree_id]
                return self._create_tree_proxy(tree_id=tree_id, tree=tree, otus=otus)
        return None
    def get_otu(self, otu_id):
        np = self._otu_cache.get(otu_id)
        if np is not None:
            return np
        ogd = self._nexml_el['otusById']
        for og in ogd.values():
            o = og.get(otu_id)
            if o is not None:
                return self._create_otu_proxy(otu_id=otu_id, otu=o)
        return None

class NexsonTreeProxy(object):
    '''Provide more natural operations by wrapping a NexSON 1.2 tree blob and its otus'''
    class NexsonNodeProxy(object):
        def __init__(self, tree, edge_id, edge, node_id=None, node=None):
            self._tree = tree
            self._node_id = node_id
            self._node = node
            self._edge_id = edge_id
            self._edge = edge
            self._otu = None
        @property
        def is_leaf(self):
            return self._tree.is_leaf(self.node_id)
        def child_iter(self):
            return self._tree.child_iter(self.node_id)
        @property
        def ott_id(self):
            return self._tree.get_ott_id(self.node)
        @property
        def edge_id(self):
            return self._edge_id
        @property
        def edge(self):
            return self._edge
        @property
        def _id(self):
            return self.node_id
        @property
        def parent(self):
            if self._edge_id is None:
                return None
            par_node_id = self.edge['@source']
            par_edge_id, par_edge = self._tree.find_edge_from_par(par_node_id)
            return self._tree._create_node_proxy_from_edge(edge_id=par_edge_id, edge=par_edge, node_id=par_node_id)
        @property
        def node_id(self):
            if self._node_id is None:
                self._node_id = self._edge['@target']
            return self._node_id
        @property
        def otu(self):
            if self._otu is None:
                otu_id, otu = self._tree._raw_otu_for_node(self.node)
                self._otu = self._tree._nexson_proxy._create_otu_proxy(otu_id=otu_id, otu=otu)
            return self._otu
        @property
        def node(self):
            if self._node is None:
                self._node = self._tree.get_nexson_node(self.node_id)
            return self._node
        def __iter__(self):
            return iter(nexson_tree_preorder_iter(self._tree,
                                                  node=self.node,
                                                  node_id=self.node_id,
                                                  edge_id=self.edge_id,
                                                  edge=self.edge))
        def preorder_iter(self):
            return iter(nexson_tree_preorder_iter(self))
    def __init__(self, tree, tree_id=None, otus=None, nexson_proxy=None):
        self._nexson_proxy = nexson_proxy
        self._nexson_tree = tree
        self._edge_by_source_id = tree['edgeBySourceId']
        self._node_by_source_id = tree['nodeById']
        self._otus = otus
        self._tree_id = tree_id
        # not part of nexson, filled on demand. will be dict of node_id -> (edge_id, edge) pair
        self._edge_by_target = None
        self._wr = None
        self._node_cache = {}
    def get_nexson_node(self, node_id):
        return self._node_by_source_id[node_id]
    def __getitem__(self, key):
        return self._nexson_tree[key]
    def __setitem__(self, key, value):
        self._nexson_tree[key] = value

    @property
    def edge_by_target(self):
        if self._edge_by_target is None:
            self._edge_by_target = reverse_edge_by_source_dict(self._edge_by_source_id, self._nexson_tree['^ot:rootNodeId'])
        return self._edge_by_target

    def find_edge_from_par(self, node_id):
        return self.edge_by_target[node_id]
    def _create_node_proxy_from_edge(self, edge_id, edge, node_id=None, node=None):
        np = self._node_cache.get(edge_id)
        if np is None:
            if self._wr is None:
                self._wr = weakref.proxy(self)
            np = NexsonTreeProxy.NexsonNodeProxy(self._wr, edge_id=edge_id, edge=edge, node_id=node_id, node=node)
            self._node_cache[edge_id] = np
        return np
    def child_iter(self, node_id):
        return nexson_child_iter(self._edge_by_source_id.get(node_id, {}), self)
    def is_leaf(self, node_id):
        return node_id not in self._edge_by_source_id
    def get_ott_id(self, node):
        return self._raw_otu_for_node(node)[0].get('^ot:ottId')
    def _raw_otu_for_node(self, node):
        otu_id = node['@otu']
        return otu_id, self._otus[otu_id]
    def annotate(self, obj, key, value):
        obj[key] = value
    def __iter__(self):
        return iter(nexson_tree_preorder_iter(self))
    def preorder_iter(self):
        return iter(nexson_tree_preorder_iter(self))
def nexson_child_iter(edict, nexson_tree_proxy):
    for edge_id, edge in edict.items():
        yield nexson_tree_proxy._create_node_proxy_from_edge(edge_id, edge)

def nexson_tree_preorder_iter(tree_proxy, node_id=None, node=None, edge_id=None, edge=None):
    '''Takes a tree in "By ID" NexSON (v1.2).  provides and iterator over:
        NexsonNodeProxy object
    where the edge of the object is the edge connectin the node to the parent.
    The first node will be the root and will have None as it's edge
    '''
    tree = tree_proxy._nexson_tree
    ebsid = tree['edgeBySourceId']
    nbid = tree['nodeById']
    if edge_id is not None:
        assert edge is not None
        if node_id is None:
            node_id = edge['@target']
        else:
            assert node_id == edge['@target']
        if node is None:
            node = nbid[node_id]
        else:
            assert node == nbid[node_id]
        yield tree_proxy._create_node_proxy_from_edge(edge_id, edge, node_id=node_id, node=node)
        root_id = node_id
    elif node_id is not None:
        if node is None:
            node = nbid[node_id]
        else:
            assert node == nbid[node_id]
        yield tree_proxy._create_node_proxy_from_edge(None, None, node_id=node_id, node=node)
        root_id = node_id
    else:
        root_id = tree['^ot:rootNodeId']
        root = nbid[root_id]
        yield tree_proxy._create_node_proxy_from_edge(None, None, node_id=root_id, node=root)
    ebtid = {}
    stack = []
    new_stack = [(i['@target'], edge_id, i) for edge_id, i in ebsid[root_id].items()]
    for target, eid, edge in new_stack:
        assert target not in ebtid
        ebtid[target] = edge
    stack.extend(new_stack)
    while stack:
        target_node_id, edge_id, edge = stack.pop()
        node = nbid[target_node_id]
        yield tree_proxy._create_node_proxy_from_edge(edge_id=edge_id, edge=edge, node_id=target_node_id)
        daughter_edges = ebsid.get(target_node_id)
        if daughter_edges is not None:
            new_stack = [(i['@target'], edge_id, i) for edge_id, i in daughter_edges.items()]
            for target, eid, edge in new_stack:
                assert target not in ebtid
                ebtid[target] = i
            stack.extend(new_stack)

