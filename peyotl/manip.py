#!/usr/bin/env python
'''Simple manipulations of data structure in peyotl
'''
from peyotl.nexson_syntax.helper import _add_uniq_value_to_dict_bf
from peyotl.nexson_syntax import BY_ID_HONEY_BADGERFISH, \
                                 convert_nexson_format, \
                                 detect_nexson_version, \
                                 get_nexml_el, \
                                 _is_by_id_hbf
from peyotl.utility import get_logger
import weakref
_LOG = get_logger(__name__)

def count_num_trees(nexson, nexson_version=None):
    if nexson_version is None:
        nexson_version = detect_nexson_version(nexson)
    nex = get_nexml_el(nexson)
    num_trees_by_group = []
    if _is_by_id_hbf(nexson_version):
        for tree_group in nex.get('treesById', {}).values():
            nt = len(tree_group.get('treeById', {}))
            num_trees_by_group.append(nt)
    else:
        trees_group = nex.get('trees', [])
        if isinstance(trees_group, dict):
            trees_group = [trees_group]
        for tree_group in trees_group:
            t = tree_group.get('tree')
            if isinstance(t, list):
                nt = len(t)
            else:
                nt = 1
            num_trees_by_group.append(nt)
    return sum(num_trees_by_group)

def iter_trees(nexson, nexson_version=None):
    '''generator over all trees in all trees elements.
    yields a tuple of 3 items:
        trees element ID,
        tree ID,
        the tree obj
    '''
    if nexson_version is None:
        nexson_version = detect_nexson_version(nexson)
    nex = get_nexml_el(nexson)
    if _is_by_id_hbf(nexson_version):
        trees_group_by_id = nex['treesById']
        group_order = nex.get('^ot:treesElementOrder', [])
        if len(group_order) < len(trees_group_by_id):
            group_order = list(trees_group_by_id.keys())
            group_order.sort()
        for trees_group_id in group_order:
            trees_group = trees_group_by_id[trees_group_id]
            tree_by_id = trees_group['treeById']
            ti_order = trees_group.get('^ot:treeElementOrder', [])
            if len(ti_order) < len(tree_by_id):
                ti_order = list(tree_by_id.keys())
                ti_order.sort()
            for tree_id in ti_order:
                tree = tree_by_id[tree_id]
                yield trees_group_id, tree_id, tree
    else:
        for trees_group in nex.get('trees', []):
            trees_group_id = trees_group['@id']
            for tree in trees_group.get('tree', []):
                tree_id = tree['@id']
                yield trees_group_id, tree_id, tree

def label_to_original_label_otu_by_id(otu_by_id):
    '''Takes a v1.2 otuById dict and, for every otu,
    checks if ot:originalLabel exists. If it does not,
    but @label does, then ot:originalLabel is set to
    @label and @label is deleted.
    '''
    for val in otu_by_id.values():
        orig = val.get('^ot:originalLabel')
        if orig is None:
            label = val.get('@label')
            if label:
                del val['@label']
                val['^ot:originalLabel'] = label

def replace_entity_references_in_meta_and_annotations(d, id2id):
    if isinstance(d, list):
        for el in d:
            replace_entity_references_in_meta_and_annotations(el, id2id)
    elif isinstance(d, dict):
        about_key = d.get('@about')
        try:
            if about_key and about_key.startswith('#'):
                s = about_key[1:]
                r = id2id.get(s)
                if r is not None:
                    d['@about'] = '#' + r
        except:
            pass
        for v in d.values():
            replace_entity_references_in_meta_and_annotations(v, id2id)

_special_otu_keys = frozenset(('@label', '^ot:originalLabel', '^ot:ottId', '^ot:ottTaxonName'))
def _merge_otu_do_not_fix_references(src, dest):
    for k in _special_otu_keys:
        if k not in dest and k in src:
            dest[k] = src[k]
    for k, v in src.items():
        if k not in _special_otu_keys:
            _add_uniq_value_to_dict_bf(dest, k, v)
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
class NexsonTreeProxy(object):
    '''Provide more natural operations by wrapping a NexSON 1.2 tree blob and its otus'''
    class NexsonNodeProxy(object):
        def __init__(self, tree, edge_id, edge, node_id=None, node=None):
            self._tree = tree
            self._node_id = node_id
            self._node = node
            self._edge_id = edge_id
            self._edge = edge
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
            return self._tree._gen_node_proxy_from_edge(edge_id=par_edge_id, edge=par_edge, node_id=par_node_id)
        @property
        def node_id(self):
            if self._node_id is None:
                self._node_id = self._edge['@target']
            return self._node_id
        @property
        def node(self):
            if self._node is None:
                self._node = self._tree['nodeById'][self.node_id]
            return self._node
        def __iter__(self):
            return iter(nexson_tree_preorder_iter(self._tree,
                                                  node=self.node,
                                                  node_id=self.node_id,
                                                  edge_id=self.edge_id,
                                                  edge=self.edge))
        def preorder_iter(self):
            return iter(nexson_tree_preorder_iter(self))
    def __init__(self, tree, tree_id=None, otus=None):
        self._nexson_tree = tree
        self._edge_by_source_id = tree['edgeBySourceId']
        self._node_by_source_id = tree['nodeById']
        self._otus = otus
        self._tree_id = tree_id
        # not part of nexson, filled on demand. will be dict of node_id -> (edge_id, edge) pair
        self._edge_by_target = Non
        self._wr = None
    @property
    def edge_by_target(self):
        if self._edge_by_target is None:
            self._edge_by_target = reverse_edge_by_source_dict(self._edge_by_source_id, self._nexson_tree['^ot:rootNodeId'])
        return self._edge_by_target

    def find_edge_from_par(self, node_id):
        return self.edge_by_target[node_id]
    def _gen_node_proxy_from_edge(self, edge_id, edge, node_id=None, node=None):
        if self._wr is None:
            self._wr = weakref.ref(self)
        return NexsonTreeProxy.NexsonNodeProxy(self._wr, edge_id=edge_id, edge=edge, node_id=node_id, node=node)
    def child_iter(self, node_id):
        return nexson_child_iter(self._edge_by_source_id.get(node_id, {}), self)
    def is_leaf(self, node_id):
        return node_id not in self._edge_by_source_id
    def get_ott_id(self, node):
        return self._otus[node['@otu']].get('^ot:ottId')
    def annotate(self, obj, key, value):
        obj[key] = value
    def __iter__(self):
        return iter(nexson_tree_preorder_iter(self))
    def preorder_iter(self):
        return iter(nexson_tree_preorder_iter(self))
def nexson_child_iter(edict, nexson_tree_proxy):
    for edge_id, edge in edict.items():
        yield nexson_tree_proxy._gen_node_proxy_from_edge(edge_id, edge)

def nexson_tree_preorder_iter(tree, node_id=None, node=None, edge_id=None, edge=None):
    '''Takes a tree in "By ID" NexSON (v1.2).  provides and iterator over:
        NexsonNodeProxy object
    where the edge of the object is the edge connectin the node to the parent.
    The first node will be the root and will have None as it's edge
    '''
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
        yield tree._gen_node_proxy_from_edge(edge_id, edge, node_id=node_id, node=node)
        root_id = node_id
    elif node_id is not None:
        if node is None:
            node = nbid[node_id]
        else:
            assert node == nbid[node_id]
        yield tree._gen_node_proxy_from_edge(None, None, node_id=node_id, node=node)
        root_id = node_id
    else:
        root_id = tree['^ot:rootNodeId']
        root = nbid[root_id]
        yield tree._gen_node_proxy_from_edge(None, None, node_id=root_id, node=root)
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
        yield tree._gen_node_proxy_from_edge(edge_id=edge_id, edge=edge, node_id=target_node_id)
        daughter_edges = ebsid.get(target_node_id)
        if daughter_edges is not None:
            new_stack = [(i['@target'], edge_id, i) for edge_id, i in daughter_edges.items()]
            for target, eid, edge in new_stack:
                assert target not in ebtid
                ebtid[target] = i
            stack.extend(new_stack)

def merge_otus_and_trees(nexson_blob):
    '''Takes a nexson object:
        1. merges trees elements 2 - # trees into the first trees element.,
        2. merges otus elements 2 - # otus into the first otus element.
        3. if there is no ot:originalLabel field for any otu,
            it sets that field based on @label and deletes @label
        4. merges an otu elements using the rule:
              A. treat (ottId, originalLabel) as a key
              B. If otu objects in subsequent trees match originalLabel and
                have a matching or absent ot:ottId, then they are merged into
                the same OTUs (however see C)
              C. No two leaves of a tree may share an otu (though otu should
                be shared across different trees). It is important that
                each leaf node be mapped to a distinct OTU. Otherwise there
                will be no way of separating them during OTU mapping. we
                do this indirectly by assuring to no two otu objects in the
                same otus object get merged with each other (or to a common
                object)

        5. correct object references to deleted entities.

    This function is used to patch up NexSONs created by multiple imports, hence the
    substitution of '@label' for 'ot:originalLabel'. Ids are arbitrary for imports from
    non-nexml tools, so matching is done based on names. This should mimic the behavior
    of the analysis tools that produced the trees (for most/all such tools unique names
    constitute unique OTUs).
    '''
    id_to_replace_id = {}
    orig_version = detect_nexson_version(nexson_blob)
    convert_nexson_format(nexson_blob, BY_ID_HONEY_BADGERFISH)
    nexson = get_nexml_el(nexson_blob)
    otus_group_order = nexson.get('^ot:otusElementOrder', [])
    # (ott, orig) -> list of otu elements
    retained_mapped2otu = {}
    # orig -> list of otu elements
    retained_orig2otu = {}
    # For the first (entirely retained) group of otus:
    #   1. assure that originalLabel is filled in
    #   2. register the otu in retained_mapped2otu and retained_orig2otu
    # otu elements that have no label, originalLabel or ottId will not
    #   be registered, so they'll never be matched.
    if len(otus_group_order) > 0:
        otus_group_by_id = nexson['otusById']
        retained_ogi = otus_group_order[0]
        retained_og = otus_group_by_id[retained_ogi]
        retained_og_otu = retained_og.setdefault('otuById', {})
        label_to_original_label_otu_by_id(retained_og_otu)
        for oid, otu in retained_og_otu.items():
            ottid = otu.get('^ot:ottId')
            orig = otu.get('^ot:originalLabel')
            key = (ottid, orig)
            if key != (None, None):
                m = retained_mapped2otu.setdefault(key, [])
                t = (oid, otu)
                m.append(t)
                if orig is not None:
                    m = retained_orig2otu.setdefault(orig, [])
                    m.append(t)
        # For each of the other otus elements, we:
        #   1. assure that originalLabel is filled in
        #   2. decide (for each otu) whether it will
        #       be added to retained_og or merged with
        #       an otu already in retained_og. In the
        #       case of the latter, we add to the
        #       replaced_otu dict (old oid as key, new otu as value)
        for ogi in otus_group_order[1:]:
            #_LOG.debug('retained_mapped2otu = {r}'.format(r=retained_mapped2otu))
            og = otus_group_by_id[ogi]
            del otus_group_by_id[ogi]
            otu_by_id = og.get('otuById', {})
            label_to_original_label_otu_by_id(otu_by_id)
            used_matches = set()
            id_to_replace_id[ogi] = retained_ogi
            for oid, otu in otu_by_id.items():
                ottid = otu.get('^ot:ottId')
                orig = otu.get('^ot:originalLabel')
                key = (ottid, orig)
                if key == (None, None):
                    retained_og[oid] = otu
                else:
                    match_otu = None
                    mlist = retained_mapped2otu.get(key)
                    if mlist is not None:
                        for m in mlist:
                            if m[0] not in used_matches:
                                # _LOG.debug('Matching {k} to {m}'.format(k=repr(key), m=repr(m)))
                                match_otu = m
                                break
                            #else:
                            #    _LOG.debug('{k} already in {m}'.format(k=repr(m[0]), m=repr(used_matches)))
                    if match_otu is None:
                        #_LOG.debug('New el: {k} mlist = {m}'.format(k=repr(key), m=repr(mlist)))
                        mlist = retained_orig2otu.get(orig, [])
                        for m in mlist:
                            if m[0] not in used_matches:
                                match_otu = m
                                break
                    if match_otu is not None:
                        id_to_replace_id[oid] = match_otu[0]
                        used_matches.add(match_otu[0])
                        _merge_otu_do_not_fix_references(otu, match_otu[1])
                    else:
                        assert oid not in retained_og_otu
                        retained_og_otu[oid] = otu
                        m = retained_mapped2otu.setdefault(key, [])
                        t = (oid, otu)
                        m.append(t)
                        if orig is not None:
                            m = retained_orig2otu.setdefault(orig, [])
                            m.append(t)
        nexson['^ot:otusElementOrder'] = [retained_ogi]
    # Move all of the tree elements to the first trees group.
    trees_group_order = nexson.get('^ot:treesElementOrder', [])
    if len(trees_group_order) > 0:
        trees_group_by_id = nexson['treesById']
        retained_tgi = trees_group_order[0]
        retained_tg = trees_group_by_id[retained_tgi]
        retained_tg['@otus'] = retained_ogi
        retained_tg_tree_obj = retained_tg.get('treeById', {})
        for tgi in trees_group_order[1:]:
            tg = trees_group_by_id[tgi]
            del trees_group_by_id[tgi]
            id_to_replace_id[tgi] = retained_tgi
            retained_tg['^ot:treeElementOrder'].extend(tg['^ot:treeElementOrder'])
            for tid, tree_obj in tg.get('treeById', {}).items():
                retained_tg_tree_obj[tid] = tree_obj
        for tree_obj in retained_tg_tree_obj.values():
            for node in tree_obj.get('nodeById', {}).values():
                o = node.get('@otu')
                if o is not None:
                    r = id_to_replace_id.get(o)
                    if r is not None:
                        node['@otu'] = r
        nexson['^ot:treesElementOrder'] = [retained_tgi]

    replace_entity_references_in_meta_and_annotations(nexson, id_to_replace_id)
    convert_nexson_format(nexson_blob, orig_version)
    return nexson_blob


