#!/usr/bin/env python
class Node(object):
    def __init__(self, _id=None):
        self._id = _id
        self._children = []
        self._parent = None
    def postorder_iter(self, filter_fn=None):
        stack = [(self, False)]
        while stack:
            node, state = stack.pop(0)
            if state:
                if filter_fn is None or filter_fn(node):
                    yield node
            else:
                stack.insert(0, (node, True))
                if node._children:
                    stack = [(n, False) for n in node.children_iter()] + stack
    def children_iter(self, filter_fn=None):
        if self._children:
            for i in self._children:
                if filter_fn is None or filter_fn(i):
                    yield i
class NodeWithPathInEdges(Node):
    def __init__(self, _id=None):
        Node.__init__(self, _id)
        if _id is not None:
            self._path_ids = [_id]
            self._path_set = set([_id])
        else:
            self._path_ids = []
            self._path_set = set()
    def add_child(self, child):
        self._children.append(child)
        child._parent = self
class TreeWithPathsInEdges(object):
    def __init__(self, id_to_par_id=None):
        self._id2par = id_to_par_id
        self._leaves = []
        self._id2node = {}
        self._root = None
    def create_leaf(self, node_id):
        n = NodeWithPathInEdges(_id=node_id)
        self._add_node(n)
        return n
    def _add_node(self, n):
        node_id = n._id
        if node_id is None:
            return
        assert node_id not in self._id2node
        self._id2node[node_id] = node_id
        self._leaves.append(n)
    def _init_with_cherry(self, i1, i2):
        n1 = self.create_leaf(node_id=i1)
        if i1 == i2:
            self.set_root(n1)
            return self
        anc1 = n1._path_ids
        curr_id1 = i1
        anc1d = n1._path_set
        extending1 = True
        n2 = self.create_leaf(node_id=i2)
        anc2 = n2._path_ids
        curr_id2 = i2
        anc2d = n2._path_set
        extending2 = True
        while True:
            assert extending1 or extending2
            if extending1:
                p1 = self._id2par.get(curr_id1)
                assert p1 not in anc1d
                if p1 is None:
                    extending1 = False
                    assert extending2
                else:
                    if p1 in anc2d:
                        return self._create_mrca(n1, n2, p1)
                    else:
                        curr_id1 = p1
                        anc1.append(p1)
                        anc1d.add(p1)
            if extending2:
                p2 = self._id2par.get(curr_id2)
                assert p2 not in anc2d
                if p2 is None:
                    extending2 = False
                    assert extending1
                else:
                    if p2 in anc1d:
                        return self._create_mrca(n2, n1, p2)
                    else:
                        curr_id2 = p2
                        anc2.append(p2)
                        anc2d.add(p2)
    def _create_mrca(self, growing, hit, mrca_id):
        assert mrca_id not in growing._path_set
        assert mrca_id in hit._path_set
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
        m.add_child(hit)
        m.add_child(growing)
        self._root = m
        return m
    def set_root(self, n):
        assert self._root is None
        self._root = n
        self._add_node(n)

    def _add_leaf_for_id(self, ott_id):
        return NotImplementedError('this is where you were coding, MTH')
    @property
    def leaves(self):
        return list(self._leaves)
    def postorder_node_iter(self, nd=None, filter_fn=None):
        if nd is None:
            nd = self._root
        return nd.postorder_iter(filter_fn=filter_fn)
def create_tree_from_id2par(id2par, id_list, _class=TreeWithPathsInEdges):
    if not id_list:
        return None
    nn = len(id_list)
    tree = _class(id_to_par_id=id2par)
    if nn == 1:
        if id_list[0] not in id2par:
            raise KeyError('The ID {} was not found'.format(id_list[0]))
        n = tree._add_leaf_for_id(id_list[0])
        tree._root = n
        del tree._id2par
        return tree
    tree._init_with_cherry(id_list[0], id_list[1])
    curr_ind = 2
    while curr_ind < nn:
        tree._add_leaf_for_id(id_list[curr_ind])
        curr_ind += 1
    del tree._id2par
    return tree


