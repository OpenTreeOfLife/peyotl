#!/usr/bin/env python
from peyotl.utility.tokenizer import NewickEvents
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

def _write_node_info_newick(out, node, **kwargs): #TODO
    '''writes a label other info (e.g. branch lengths) based on
    kwargs:
        #TODO
    '''
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
    def is_leaf(self):
        return not bool(self._children)
    @property
    def is_first_child_of_parent(self):
        '''Returns True for *ROOT* and any node that is the first child of its parent'''
        return (self._parent is None) or (self._parent._children[0] is self)
    @property
    def is_last_child_of_parent(self):
        '''Returns True for *ROOT* and any node that is the last child of its parent'''
        return (self._parent is None) or (self._parent._children[-1] is self)
    def before_after_apply(self, before_fn, after_fn, leaf_fn=None):
        '''Applies the functions to each node in a subtree using an traversal in which
        encountered twice: once right before its descendants, and once right
        after its last descendant
        '''
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
    def __init__(self, _id=None):
        Node.__init__(self, _id)
        if _id is not None:
            self._path_ids = [_id]
            self._path_set = set([_id])
        else:
            self._path_ids = []
            self._path_set = set()
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
    def _init_with_cherry(self, i1, i2):
        n1 = self.create_leaf(node_id=i1, register_node=False)
        if i1 == i2:
            self.set_root(n1)
            return self
        anc1 = n1._path_ids
        curr_id1 = i1
        anc1d = n1._path_set
        extending1 = True
        n2 = self.create_leaf(node_id=i2, register_node=False)
        anc2 = n2._path_ids
        curr_id2 = i2
        anc2d = n2._path_set
        extending2 = True
        while True:
            if not (extending1 or extending2):
                raise ValueError('Disconnected tips cannot be used to build a tree')
            if extending1:
                p1 = self._id2par[curr_id1]
                assert p1 not in anc1d
                if p1 is None:
                    extending1 = False
                    self._root_tail_hits_real_root = True
                else:
                    if p1 in anc2d:
                        return self._init_create_mrca(n1, n2, p1)
                    else:
                        curr_id1 = p1
                        anc1.append(p1)
                        anc1d.add(p1)
            if extending2:
                p2 = self._id2par[curr_id2]
                assert p2 not in anc2d
                if p2 is None:
                    extending2 = False
                    self._root_tail_hits_real_root = True
                else:
                    if p2 in anc1d:
                        return self._init_create_mrca(n2, n1, p2)
                    else:
                        curr_id2 = p2
                        anc2.append(p2)
                        anc2d.add(p2)
    def _add_node_for_id(self, ott_id):
        #_LOG.debug('_add_node_for_id({o})'.format(o=ott_id))
        if ott_id in self._id2node:
            return
        n1 = self.create_leaf(node_id=ott_id, register_node=False)
        anc1 = n1._path_ids
        curr_id1 = ott_id
        anc1d = n1._path_set
        extending1 = True
        #_LOG.debug('anc1d at start = {}'.format(anc1d))
        n2 = self._root
        if self._root_tail_hits_real_root:
            extending2 = False
        else:
            extending2 = True
            anc2 = n2._path_ids
            curr_id2 = anc2[-1]
        anc2d = self._id2node
        #_LOG.debug('curr_id2 = {}  anc2d at start = {}'.format(curr_id2, anc2d.keys()))
        while True:
            if not (extending1 or extending2):
                raise ValueError('Disconnected tips cannot be used to build a tree')
            if extending1:
                p1 = self._id2par[curr_id1]
                assert p1 not in anc1d
                if p1 is None:
                    extending1 = False
                    self._root_tail_hits_real_root = True
                else:
                    if p1 in anc2d:
                        #_LOG.debug(' lineage 1 hit the tree at {}'.format(p1))
                        return self._new_tip_hit_existing_tree(n1, p1)
                    else:
                        curr_id1 = p1
                        anc1.append(p1)
                        anc1d.add(p1)
                        #_LOG.debug('anc1d is now = {} after the addition of {}'.format(anc1d, p1))
            if extending2:
                p2 = self._id2par[curr_id2]
                #_LOG.debug('p2 = {p} anc2d={a}'.format(p=p2, a=anc2d.keys()))
                assert p2 not in anc2d
                if p2 is None:
                    extending2 = False
                    self._root_tail_hits_real_root = True
                else:
                    if p2 in anc1d:
                        #_LOG.debug(' the "root tail" of the tree hit the new lineage at {}'.format(p2))
                        return self._existing_tree_hit_new_tip(n2, n1, p2)
                    else:
                        curr_id2 = p2
                        anc2d[p2] = n2
                        anc2.append(p2)
                        n2._path_set.add(p2)
                        #_LOG.debug('anc2d is now = {} after the addition of {}'.format(anc2d.keys(), p2))
    def _new_tip_hit_existing_tree(self, growing, mrca_id):
        assert mrca_id not in growing._path_set
        node_for_mrca = self._id2node[mrca_id]
        if mrca_id == node_for_mrca._id:
            node_for_mrca.add_child(growing)
            self._register_node(growing)
            if mrca_id in self._leaves:
                self._leaves.remove(mrca_id)
            return node_for_mrca
        return self._init_create_mrca(growing, node_for_mrca, mrca_id, register_hit_ids=False)

    def _existing_tree_hit_new_tip(self, growing, hit, mrca_id):
        assert mrca_id not in growing._path_set
        return self._init_create_mrca(growing, hit, mrca_id, register_hit_ids=True)


    def _init_create_mrca(self, growing, hit, mrca_id, register_hit_ids=True):
        assert mrca_id not in growing._path_set
        assert mrca_id in hit._path_set
        #_LOG.debug('_init_create_mrca growing._path_ids = {}'.format(growing._path_ids))
        if mrca_id == hit._id:
            if hit._children:
                #_LOG.debug('_init_create_mrca the mrca ID ({}) is the end of an internal node path'.format(mrca_id))
                hit.add_child(growing)
                self._register_node(growing)
            else:
                #_LOG.debug('_init_create_mrca the mrca ID ({}) is the tip of a path'.format(mrca_id))
                hit._path_ids = growing._path_ids + hit._path_ids
                hit._path_set.update(growing._path_set)
                self._leaves.remove(hit._id)
                hit._id = growing._id
                self._register_node(hit)
            return hit

        #_LOG.debug('_init_create_mrca the mrca ID ({}) is inside a path that ends with {}'.format(mrca_id, hit._id))
        m = NodeWithPathInEdges(mrca_id)
        rs = m._path_set
        rl = m._path_ids
        h_anc = hit._path_ids
        h_s = hit._path_set
        next_id = h_anc.pop()
        h_s.remove(next_id)
        while next_id != mrca_id:
            rs.add(next_id)
            rl.insert(1, next_id) # the mrca should stay el 0, we add the other elements in reverse order
            next_id = h_anc.pop()
            h_s.remove(next_id)
        m._mrca_node_for = set([mrca_id])
        m._mrca_node_for.update(growing._path_set)
        m._mrca_node_for.update(h_s)
        if hit._parent:
            hit._parent.replace_child(hit, m)
        m.add_child(hit)
        m.add_child(growing)
        #_LOG.debug('new mrca node {} created with children {}'.format(m._id, [i._id for i in m._children]))
        if (self._root is None) or (self._root is hit) or (self._root is growing):
            #_LOG.debug('_root reset to {}'.format(m._id))
            self._root = m
        self._register_node(growing)
        if register_hit_ids:
            self._register_node(hit)
        self._register_node(m)
        return m
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
        '''Adds a long integer bits4subtree_ids to each node (Fails cryptically if that field is already present!)
        relevant_ids can be a dict of _id to bit representation.
        If it is not supplied, a dict will be created by registering the leaf._id into a dict (and returning the dict)
        the bits4subtree_ids will have a 1 bit if the _id is at or descended from this node and 0 if it is not
            in this subtree.
        Returns the dict of ids -> longs
        Also creates a dict of long -> node mappings for all internal nodes. Stores this in self as bits2internal_node
        '''
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
            #_LOG.debug('node._id ={}'.format(i))
            #_LOG.debug('Before par mrca... = {}'.format(p.bits4subtree_ids))
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
            #_LOG.debug('while add bitrep... self.bits2internal_node = {}'.format(self.bits2internal_node))
            p.bits4subtree_ids |= node.bits4subtree_ids
        return relevant_ids
def create_tree_from_id2par(id2par, id_list, _class=TreeWithPathsInEdges):
    if not id_list:
        return None
    nn = len(id_list)
    tree = _class(id_to_par_id=id2par)
    if nn == 1:
        if id_list[0] not in id2par:
            raise KeyError('The ID {} was not found'.format(id_list[0]))
        n = tree.create_leaf(id_list[0])
        tree._root = n
        del tree._id2par
        return tree
    tree._init_with_cherry(id_list[0], id_list[1])
    curr_ind = 2
    while curr_ind < nn:
        next_id = id_list[curr_ind]
        tree._add_node_for_id(next_id)
        curr_ind += 1
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
                #_LOG.debug(node._children)
                testCase.assertNotIn(node._id, leaf_ids)

    else:
        anc_ref_count = {}
        anc_set = set()
        checked_node = set()
        #_LOG.debug('post_order_ids = {}'.format(post_order_ids))
        for t in leaf_ids:
            anc_id = id2par[t]
            #_LOG.debug('anc_id = {}'.format(anc_id))
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
                #_LOG.debug('anc_id = {}'.format(anc_id))
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
            #_LOG.debug('anc_set = {}'.format(anc_set))
            #_LOG.debug('checked_node = {}'.format(checked_node))
    if len(tree._id2node) > 1:
        from peyotl.utility.str_util import StringIO
        o = StringIO()
        tree.write_newick(o)
        from peyotl.utility.tokenizer import NewickEventFactory
        nef = NewickEventFactory(newick=o.getvalue())
        ptree = TreeWithPathsInEdges(newick_events=nef)

def parse_newick(newick=None, stream=None, filepath=None, _class=TreeWithPathsInEdges):
    from peyotl.utility.tokenizer import NewickEventFactory, NewickTokenizer
    nt = NewickTokenizer(stream=stream, newick=newick, filepath=filepath)
    nef = NewickEventFactory(tokenizer=nt)
    return _class(newick_events=nef)

