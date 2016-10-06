#!/usr/bin/env python
from peyotl.utility.tokenizer import NewickEvents
from peyotl.utility import get_logger
import sys

_LOG = get_logger(__name__)


def _write_node_info_newick(out, node, **kwargs):  # TODO
    """writes a label other info (e.g. branch lengths) based on
    kwargs:
        #TODO
    """
    out.write(str(node._id))


class ExtensibleObject(object):
    pass


class Node(object):
    def __init__(self, _id=None):
        self._id = _id
        self._children = []
        self._parent = None
        self._edge = None

    @property
    def parent(self):
        return self._parent

    @property
    def edge(self):
        if self._edge is None:
            self._edge = ExtensibleObject()
        return self._edge

    def sib_iter(self):
        if self._parent is None:
            raise StopIteration
        for c in self._parent.child_iter():
            if c is not self:
                yield c

    def child_iter(self):
        return iter(self._children)

    @property
    def children(self):
        return tuple(self._children)

    @property
    def is_leaf(self):
        return not bool(self._children)

    @property
    def is_first_child_of_parent(self):
        """Returns True for *ROOT* and any node that is the first child of its parent"""
        return (self._parent is None) or (self._parent._children[0] is self)

    @property
    def is_last_child_of_parent(self):
        """Returns True for *ROOT* and any node that is the last child of its parent"""
        return (self._parent is None) or (self._parent._children[-1] is self)

    def before_after_apply(self, before_fn, after_fn, leaf_fn=None):
        """Applies the functions to each node in a subtree using an traversal in which
        encountered twice: once right before its descendants, and once right
        after its last descendant
        """
        stack = [self]
        while stack:
            node = stack.pop()
            if node.is_leaf:
                if leaf_fn:
                    leaf_fn(node)
                while node.is_last_child_of_parent:
                    node = node._parent
                    if node:
                        after_fn(node)
                    else:
                        break
            else:
                before_fn(node)
                stack.extend([i for i in reversed(node._children)])

    def preorder_iter(self, filter_fn=None):
        """ From DendroPy
        Preorder traversal of self and its child_nodes.  Returns self
        and all descendants such that a node is returned before its
        child_nodes (and their child_nodes). Filtered by filter_fn: node is
        only returned if no filter_fn is given or if filter_fn returns
        True.
        """
        stack = [self]
        while stack:
            node = stack.pop()
            if filter_fn is None or filter_fn(node):
                yield node
            stack.extend([i for i in reversed(node._children)])

    def postorder_iter(self, filter_fn=None):
        """From DendroPy
        Postorder traversal of the self and its child_nodes.  Returns self
        and all descendants such that a node's child_nodes (and their
        child_nodes) are visited before node.  Filtered by filter_fn:
        node is only returned if no filter_fn is given or if filter_fn
        returns True.
        """
        stack = [(self, False)]
        while stack:
            node, state = stack.pop()
            if state:
                if filter_fn is None or filter_fn(node):
                    yield node
            else:
                stack.append((node, True))
                if node._children:
                    stack.extend([(n, False) for n in node.children_reversed_iter()])

    def children_iter(self, filter_fn=None):
        if self._children:
            for i in self._children:
                if filter_fn is None or filter_fn(i):
                    yield i

    def children_reversed_iter(self, filter_fn=None):
        if self._children:
            for i in reversed(self._children):
                if filter_fn is None or filter_fn(i):
                    yield i

    def add_child(self, child):
        child._child_index_in_parent = len(self._children)
        self._children.append(child)
        child._parent = self

    def add_sib(self, sib):
        self._parent.add_child(sib)

    def replace_child(self, old_child, new_c):
        i = old_child._child_index_in_parent
        assert self._children[i] is old_child
        del old_child._child_index_in_parent
        self._children[i] = new_c
        new_c._child_index_in_parent = i
        new_c._parent = self


class NodeWithPathInEdges(Node):
    def __init__(self, _id=None, path_ids=None):
        Node.__init__(self, _id)
        if path_ids is not None:
            self._path_ids = list(path_ids)
        else:
            if _id is not None:
                self._path_ids = [_id]
            else:
                self._path_ids = []
        self._path_set = set(self._path_ids)


class _TreeWithNodeIDs(object):
    def __init__(self):
        self._id2node = {}
        self._leaves = set()
        self._root = None

    @property
    def root(self):
        return self._root

    def find_node(self, _id):
        return self._id2node[_id]

    def _register_node(self, node):
        i = node._id
        self._id2node[i] = node
        if node.is_leaf:
            self._leaves.add(i)
        elif i in self._leaves:
            self._leaves.remove(i)
        for i in node._path_ids:
            self._id2node[i] = node

    def do_full_check_of_invariants(self, testCase, **kwargs):
        _do_full_check_of_tree_invariants(self, testCase, **kwargs)

    def write_newick(self, out, **kwargs):
        def _open_newick(node):
            if node.is_first_child_of_parent:
                out.write('(')
            else:
                out.write(',(')

        def _t(node):
            if not node.is_first_child_of_parent:
                out.write(',')
            _write_node_info_newick(out, node, **kwargs)

        def _a(node):
            out.write(')')
            _write_node_info_newick(out, node, **kwargs)

        self._root.before_after_apply(before_fn=_open_newick, after_fn=_a, leaf_fn=_t)
        out.write(';\n')


class SpikeTreeError(Exception):
    def __init__(self, anc):
        self.anc = anc


class TreeWithPathsInEdges(_TreeWithNodeIDs):
    def __init__(self, id_to_par_id=None, newick_events=None):
        _TreeWithNodeIDs.__init__(self)
        if id_to_par_id:
            self._id2par = id_to_par_id
            self._root_tail_hits_real_root = False
        else:
            self._id2par = None
            self._root_tail_hits_real_root = False
            if newick_events is not None:
                self._build_from_newick_events(newick_events)

    def _build_from_newick_events(self, ev):
        iev = iter(ev)
        assert next(iev)['type'] == NewickEvents.OPEN_SUBTREE
        self._root = NodeWithPathInEdges(_id=None)
        curr = self._root
        prev = NewickEvents.OPEN_SUBTREE
        for event in iev:
            t = event['type']
            if t == NewickEvents.OPEN_SUBTREE:
                n = NodeWithPathInEdges(_id=None)
                if prev == NewickEvents.OPEN_SUBTREE:
                    curr.add_child(n)
                else:
                    curr.add_sib(n)
                curr = n
            elif t == NewickEvents.TIP:
                n = NodeWithPathInEdges(_id=event['label'])
                if prev == NewickEvents.OPEN_SUBTREE:
                    curr.add_child(n)
                else:
                    curr.add_sib(n)
                curr = n
                self._id2node[n._id] = n
                self._leaves.add(curr)
            else:
                assert t == NewickEvents.CLOSE_SUBTREE
                curr = curr._parent
                x = event.get('label')
                if x is not None:
                    curr._id = x
                    self._id2node[x] = curr
            prev = t
        assert curr is self._root

    @property
    def leaf_ids(self):
        return [i for i in self.leaf_id_iter()]

    def leaf_id_iter(self):
        return iter(self._leaves)

    def create_leaf(self, node_id, register_node=True):
        n = NodeWithPathInEdges(_id=node_id)
        self._add_node(n, register_node=register_node)
        return n

    def _add_node(self, n, register_node=True):
        node_id = n._id
        if node_id is None:
            return
        assert node_id not in self._id2node
        if register_node:
            self._register_node(n)

    def set_root(self, n):
        assert self._root is None
        self._root = n
        self._add_node(n)

    @property
    def leaves(self):
        return [self._id2node[i] for i in self._leaves]

    def postorder_node_iter(self, nd=None, filter_fn=None):
        if nd is None:
            nd = self._root
        return nd.postorder_iter(filter_fn=filter_fn)

    def preorder_node_iter(self, nd=None, filter_fn=None):
        if nd is None:
            nd = self._root
        return nd.preorder_iter(filter_fn=filter_fn)

    def __iter__(self):
        return self._root.preorder_iter()

    def add_bits4subtree_ids(self, relevant_ids):
        """Adds a long integer bits4subtree_ids to each node (Fails cryptically if that field is already present!)
        relevant_ids can be a dict of _id to bit representation.
        If it is not supplied, a dict will be created by registering the leaf._id into a dict (and returning the dict)
        the bits4subtree_ids will have a 1 bit if the _id is at or descended from this node and 0 if it is not
            in this subtree.
        Returns the dict of ids -> longs
        Also creates a dict of long -> node mappings for all internal nodes. Stores this in self as bits2internal_node
        """
        if relevant_ids:
            checking = True
        else:
            checking = False
            relevant_ids = {}
            bit = 1
        self.bits2internal_node = {}
        for node in self.postorder_node_iter():
            p = node._parent
            if p is None:
                if not node.is_leaf:
                    self.bits2internal_node[node.bits4subtree_ids] = node
                continue
            if not hasattr(p, 'bits4subtree_ids'):
                p.bits4subtree_ids = 0
            i = node._id
            # _LOG.debug('node._id ={}'.format(i))
            # _LOG.debug('Before par mrca... = {}'.format(p.bits4subtree_ids))
            if checking:
                b = relevant_ids.get(i)
                if b:
                    if node.is_leaf:
                        node.bits4subtree_ids = b
                    else:
                        node.bits4subtree_ids |= b
            else:
                if node.is_leaf:
                    relevant_ids[i] = bit
                    node.bits4subtree_ids = bit
                    bit <<= 1
            if not node.is_leaf:
                self.bits2internal_node[node.bits4subtree_ids] = node
            # _LOG.debug('while add bitrep... self.bits2internal_node = {}'.format(self.bits2internal_node))
            p.bits4subtree_ids |= node.bits4subtree_ids
        return relevant_ids


def create_anc_lineage_from_id2par(id2par_id, ott_id):
    """Returns a list from [ott_id, ott_id's par, ..., root ott_id]"""
    curr = ott_id
    n = id2par_id.get(curr)
    if n is None:
        raise KeyError('The OTT ID {} was not found'.format(ott_id))
    lineage = [curr]
    while n is not None:
        lineage.append(n)
        n = id2par_id.get(n)
    return lineage


def create_tree_from_id2par(id2par,
                            id_list,
                            _class=TreeWithPathsInEdges,
                            create_monotypic_nodes=False):
    if not id_list:
        return None
    f = id_list.pop(0)
    anc_spike = create_anc_lineage_from_id2par(id2par, f)
    # _LOG.debug('anc_spike = {}'.format(anc_spike))
    assert f == anc_spike[0]
    tree = _class(id_to_par_id=id2par)
    if not id_list:
        n = tree.create_leaf(f)
        tree._root = n
        del tree._id2par
        return tree
    # build a dictionary of par ID to sets of children
    realized_to_children = {f: set()}
    root_nd = anc_spike[-1]
    for n, child in enumerate(anc_spike[:-1]):
        par = anc_spike[n + 1]
        realized_to_children[par] = {child}
    id_set = {f}
    for ott_id in id_list:
        id_set.add(ott_id)
        if ott_id in realized_to_children:
            _LOG.debug('element of id_list is a duplicate or ancestor or another element')
            continue
        realized_to_children[ott_id] = set()
        while True:
            par = id2par[ott_id]
            if par is None:
                raise ValueError('Id "{}" not found in id to parent mapping'.format(ott_id))
            par_realized_children = realized_to_children.get(par)
            if par_realized_children is None:
                realized_to_children[par] = {ott_id}
            else:
                if ott_id not in par_realized_children:
                    par_realized_children.add(ott_id)
                break
            ott_id = par
    # Walk from the root to the "first fork"
    rc = realized_to_children[root_nd]
    while len(rc) == 1:
        if root_nd in id_set:
            break
        root_nd = rc.pop()
        rc = realized_to_children[root_nd]
    # Now create a map from parent to (leaf_or_internal_des, [child, grandchild, ..., par_of_leaf_or_internal])
    to_process = [root_nd]
    tree._root = NodeWithPathInEdges(_id=root_nd)
    id2tree_node = {root_nd: tree._root}
    while to_process:
        nd_id = to_process.pop(0)
        nd = id2tree_node[nd_id]
        c_id_set = realized_to_children[nd_id]
        for child_id in c_id_set:
            des_id = child_id
            dc_id_set = realized_to_children[des_id]
            path_ids = []
            if create_monotypic_nodes:
                path_ids.append(des_id)
            else:
                while len(dc_id_set) == 1:
                    path_ids.append(des_id)
                    des_id = dc_id_set.pop()
                    dc_id_set = realized_to_children[des_id]
                path_ids.append(des_id)
                path_ids.reverse()
            # _LOG.debug('NodeWithPathInEdges({}, path_ids={})'.format(des_id, path_ids))
            nn = NodeWithPathInEdges(des_id, path_ids=path_ids)
            id2tree_node[des_id] = nn
            nd.add_child(nn)
            if dc_id_set:
                to_process.append(des_id)
            else:
                tree._register_node(nn)
        tree._register_node(nd)
    del tree._id2par
    return tree


def _do_full_check_of_tree_invariants(tree, testCase, id2par=None, leaf_ids=None):
    post_order = [nd for nd in tree.postorder_node_iter()]
    post_order_ids = []
    psio = set()
    for node in post_order:
        i = node._id
        testCase.assertNotIn(i, psio)
        testCase.assertIn(i, tree._id2node)
        psio.add(i)
        post_order_ids.append(i)
    pre_order = [nd for nd in tree.preorder_node_iter()]
    pre_order_ids = []
    prsio = set()
    for node in pre_order:
        i = node._id
        prsio.add(i)
        pre_order_ids.append(i)
    testCase.assertEqual(psio, prsio)
    for i in tree._id2node.keys():
        testCase.assertIn(i, psio)

    if leaf_ids is None:
        leaf_ids = [i for i in tree.leaf_id_iter()]
    for i in leaf_ids:
        testCase.assertIn(i, tree._leaves)

    if not id2par:
        for l in leaf_ids:
            testCase.assertTrue(l in psio)
        for node in post_order:
            if node.is_leaf:
                testCase.assertIn(node._id, leaf_ids)
            else:
                # _LOG.debug(node._children)
                testCase.assertNotIn(node._id, leaf_ids)

    else:
        anc_ref_count = {}
        anc_set = set()
        checked_node = set()
        # _LOG.debug('post_order_ids = {}'.format(post_order_ids))
        for t in leaf_ids:
            anc_id = id2par[t]
            # _LOG.debug('anc_id = {}'.format(anc_id))
            anc_ref_count[anc_id] = 1 + anc_ref_count.get(anc_id, 0)
            if anc_ref_count[anc_id] > 1:
                anc_set.add(anc_id)
            testCase.assertTrue(tree.find_node(t).is_leaf)
            testCase.assertIn(t, post_order_ids)
            if (anc_id in tree._id2node) and (anc_id == tree.find_node(anc_id)._id):
                testCase.assertIn(anc_id, post_order_ids)
                testCase.assertLess(post_order_ids.index(t), post_order_ids.index(anc_id))
                testCase.assertGreater(pre_order_ids.index(t), pre_order_ids.index(anc_id))
            else:
                testCase.assertNotIn(anc_id, psio)
            checked_node.add(t)
        while len(anc_set - checked_node) > 0:
            ns = set()
            for t in anc_set:
                if t in checked_node:
                    continue
                testCase.assertNotIn(t, leaf_ids)
                testCase.assertFalse(tree.find_node(t).is_leaf)
                anc_id = id2par[t]
                # _LOG.debug('anc_id = {}'.format(anc_id))
                anc_ref_count[anc_id] = 1 + anc_ref_count.get(anc_id, 0)
                if anc_ref_count[anc_id] > 1:
                    ns.add(anc_id)
                testCase.assertIn(t, psio)
                checked_node.add(t)
                if anc_id is not None:
                    if (anc_id in tree._id2node) and (anc_id == tree.find_node(anc_id)._id):
                        testCase.assertIn(anc_id, psio)
                        testCase.assertLess(post_order_ids.index(t), post_order_ids.index(anc_id))
                        testCase.assertGreater(pre_order_ids.index(t), pre_order_ids.index(anc_id))
                    else:
                        testCase.assertNotIn(anc_id, psio)
            anc_set.update(ns)
            # _LOG.debug('anc_set = {}'.format(anc_set))
            # _LOG.debug('checked_node = {}'.format(checked_node))
    if len(tree._id2node) > 1:
        from peyotl.utility.str_util import StringIO
        o = StringIO()
        tree.write_newick(o)
        from peyotl.utility.tokenizer import NewickEventFactory
        nef = NewickEventFactory(newick=o.getvalue())
        TreeWithPathsInEdges(newick_events=nef)


def parse_newick(newick=None, stream=None, filepath=None, _class=TreeWithPathsInEdges):
    from peyotl.utility.tokenizer import NewickEventFactory, NewickTokenizer
    nt = NewickTokenizer(stream=stream, newick=newick, filepath=filepath)
    nef = NewickEventFactory(tokenizer=nt)
    return _class(newick_events=nef)


def parse_id2par_dict(id2par=None,
                      id_list=None,
                      id2par_stream=None,
                      id2par_filepath=None,
                      id_list_stream=None,
                      id_list_filepath=None,
                      _class=TreeWithPathsInEdges):
    """Expecting a dict of id2parent ID or a pickled object (passed in as file object `stream` or `filepath`)
    """
    import pickle
    if id2par is None:
        if id2par_stream is None:
            with open(id2par_filepath, 'rb') as fo:
                id2par = pickle.load(fo)
        else:
            id2par = pickle.load(id2par_stream)
    if id_list is None:
        if id_list_stream is None:
            if id_list_filepath is None:
                ancs = set(id2par.values())
                all_keys = set(id2par.keys())
                id_list = list(all_keys - ancs)
            else:
                with open(id_list_filepath, 'rb') as fo:
                    id_list = pickle.load(fo)
        else:
            id_list = pickle.load(id_list_stream)

    _LOG.debug("num els {}".format(len(id2par)))
    return create_tree_from_id2par(id2par=id2par, id_list=id_list, _class=_class)
