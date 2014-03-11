#!/usr/bin/env python
from peyotl.nexson_validation.helper import _NEXEL
from peyotl.nexson_validation.err_generator import gen_InvalidKeyWarning, \
                                                   gen_MissingCrucialContentWarning, \
                                                   gen_MissingMandatoryKeyWarning, \
                                                   gen_MultipleRootsWarning, \
                                                   gen_NodeWithMultipleParents, \
                                                   gen_NoRootWarning, \
                                                   gen_ReferencedIDNotFoundWarning, \
                                                   gen_RepeatedOTUWarning, \
                                                   gen_TreeCycleWarning
from peyotl.nexson_syntax.helper import add_literal_meta, \
                                        BADGER_FISH_NEXSON_VERSION, \
                                        delete_first_literal_meta, \
                                        find_val_for_first_bf_l_meta
from peyotl.nexson_validation._validation_base import NexsonValidationAdaptor
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

class BadgerFishValidationAdaptor(NexsonValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)
        self._syntax_version = BADGER_FISH_NEXSON_VERSION
        self._otuid2ottid_byogid = {}
        self._ottid2otuid_list_byogid = {}
        self._dupottid_by_ogid_tree_id = {}


    def _post_key_check_validate_otus_obj(self, og_nex_id, otus_group, vc):
        otu_dict = {}
        otu_list = otus_group.get('otu')
        if otu_list and isinstance(otu_list, dict):
            otu_list = [otu_list]
        if not otu_list:
            self._error_event(_NEXEL.OTUS,
                             obj=otus_group,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=og_nex_id,
                             key_list=['otu'])
            return False
        vc.push_context(_NEXEL.OTU, (otus_group, og_nex_id))
        try:
            without_id = []
            otu_tuple_list = []
            for otu in otu_list:
                oid = otu.get('@id')
                if oid is None:
                    without_id.append(otu)
                else:
                    otu_tuple_list.append((oid, otu))
                otu_dict[oid] = otu
            if without_id:
                self._error_event(_NEXEL.NEXML,
                                  obj=without_id,
                                  err_type=gen_MissingCrucialContentWarning,
                                  anc=vc.anc_list,
                                  obj_nex_id=None,
                                  key_list=['@id'])
                return False
            r = self._validate_otu_list(otu_tuple_list, vc)
            if r:
                self._otu_by_otug[og_nex_id] = otu_dict
            return r
        except:
            vc.pop_context()

    def _post_key_check_validate_tree_group(self, tg_nex_id, trees_group, vc):
        otus_el = trees_group.get('@otus')
        if otus_el not in self._otu_group_by_id:
            kl = ['@otus="{oe}"'.format(oe=otus_el)]
            self._error_event(_NEXEL.TREES,
                               obj=trees_group,
                               err_type=gen_ReferencedIDNotFoundWarning,
                               anc=vc.anc_list,
                               obj_nex_id=tg_nex_id,
                               key_list=kl)
            return False
        tree_list = trees_group.get('tree')
        if isinstance(tree_list, dict):
            tree_list = [tree_list]
        elif (not tree_list) or (not isinstance(tree_list, list)):
            self._error_event(_NEXEL.TREES,
                             obj=trees_group,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tg_nex_id,
                             key_list=['tree'])
            return False
        for tree_obj in tree_list:
            t_nex_id = tree_obj.get('@id')
            vc.push_context(_NEXEL.TREE, (tree_obj, t_nex_id))
            try:
                if t_nex_id is None:
                    self._error_event(_NEXEL.TREE,
                                  obj=tree_obj,
                                  err_type=gen_MissingCrucialContentWarning,
                                  anc=vc.anc_list,
                                  obj_nex_id=tg_nex_id,
                                  key_list=['@id'])
                    return False
                if not self._validate_tree(t_nex_id,
                                           tree_obj,
                                           vc,
                                           otus_group_id=otus_el):
                    return True
            finally:
                vc.pop_context()
        return True


    def _post_key_check_validate_tree(self,
                                      tree_nex_id,
                                      tree_obj,
                                      vc,
                                      otus_group_id=None):
        node_list = tree_obj.get('node')
        if isinstance(node_list, dict):
            node_list = [node_list]
        elif (not node_list) or (not isinstance(node_list, list)):
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['node',])
            return False
        edge_list = tree_obj.get('edge')
        if isinstance(edge_list, dict):
            edge_list = [edge_list]
        elif (not edge_list) or (not isinstance(edge_list, dict)):
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['edge',])
            return False
        if otus_group_id is None:
            tree_group = vc.anc_list[-1][1]
            otus_group_id = tree_group.get('@otus')

        lowest_nodeid_set = set()
        encountered_nodes = set()
        edge_by_target = {}
        edge_by_source = {}
        multi_parent_node = []
        for e in edge_list:
            t = e.get('@target')
            if t in edge_by_target:
                multi_parent_node.append(t)
            else:
                edge_by_target[t] = e
            edge_by_source.setdefault('@source', []).append(e)
        if multi_parent_node:
            self._error_event(_NEXEL.TREE,
                              obj=tree_obj,
                              err_type=gen_NodeWithMultipleParents,
                              anc=vc.anc_list,
                              obj_nex_id=tree_nex_id,
                              node_id_list=multi_parent_node)
        otuid2leaf = {}
        unflagged_leaves = []
        nonleaves_with_leaf_flags = []
        with_at_root_prop = {}
        first_lowest_node = None
        for nd in node_list:
            nid = nd.get('@id')
            cycle_node, path_to_root = construct_path_to_root(nd, encountered_nodes, edge_by_target)
            if cycle_node:
                self._error_event(_NEXEL.TREE,
                                  obj=tree_obj,
                                  err_type=gen_TreeCycleWarning,
                                  anc=vc.anc_list,
                                  obj_nex_id=tree_nex_id,
                                  cycle_node=cycle_node)
                return False
            if path_to_root:
                lowest_nodeid_set.add(path_to_root[-1])
                if first_lowest_node is None:
                    first_lowest_node = path_to_root[-1]
            is_flagged_as_leaf = find_val_for_first_bf_l_meta(nd, 'ot:isLeaf')
            ch_list = edge_by_source[nid]
            if len(ch_list) == 0:
                otu_id = nd.get('@otu')
                if otu_id is None:
                    vc.push_context(_NEXEL.NODE, (tree_nex_id, tree_obj))
                    try:
                        self._error_event(_NEXEL.NODE,
                                         obj=nd,
                                         err_type=gen_MissingCrucialContentWarning,
                                         anc=vc.anc_list,
                                         obj_nex_id=nid,
                                         key_list=['@otu',])
                        return False
                    finally:
                        vc.pop_context()
                else:
                    if otu_id in otuid2leaf:
                        vc.push_context(_NEXEL.NODE, (tree_nex_id, tree_obj))
                        try:
                            self._error_event(_NEXEL.NODE,
                                             obj=nd,
                                             err_type=gen_RepeatedOTUWarning,
                                             anc=vc.anc_list,
                                             obj_nex_id=nid,
                                             key_list=[otu_id])
                            return False
                        finally:
                            vc.pop_context()
                    otuid2leaf[otu_id] = nd
                if not is_flagged_as_leaf:
                    if not self._logger.retain_deprecated:
                        add_literal_meta(nd, 'ot:isLeaf', True, self._syntax_version)
                    else:
                        unflagged_leaves.append(nid)
            elif is_flagged_as_leaf:
                if not self._logger.retain_deprecated:
                    delete_first_literal_meta(nd, 'ot:isLeaf', self._syntax_version)
                else:
                    nonleaves_with_leaf_flags.append(nid)
            if nd.get('@root'):
                with_at_root_prop[nid] = nd
        
        if unflagged_leaves:
            vc.push_context(_NEXEL.NODE, (tree_nex_id, tree_obj))
            try:
                self._error_event(_NEXEL.NODE,
                                 obj=tree_obj,
                                 err_type=gen_MissingMandatoryKeyWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=unflagged_leaves,
                                 key_list=['ot:isLeaf'])
                return False
            finally:
                vc.pop_context()
        if nonleaves_with_leaf_flags:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_InvalidKeyWarning,
                             anc=vc.anc_list,
                             obj_nex_id=nonleaves_with_leaf_flags,
                             key_list=['ot:isLeaf'])
            return False
        self._detect_multilabelled_tree(otus_group_id,
                                        tree_nex_id,
                                        otuid2leaf)
        if len(lowest_nodeid_set) > 1:
            lowest_nodeid_set = list(lowest_nodeid_set)
            lowest_nodeid_set.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             node_id_list=lowest_nodeid_set)
            return False
        root_node_id = first_lowest_node.get('@id')

        if root_node_id not in with_at_root_prop:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             node_id_list=with_at_root_prop.keys() + [root_node_id])
            return False
        elif len(with_at_root_prop) > 1:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             node_id_list=with_at_root_prop.keys())
            return False
        elif len(with_at_root_prop) == 0:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_NoRootWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id)
            return False
        return True

    def _fill_otu_ottid_maps(self, otus_group_id):
        if self._otuid2ottid_byogid.get(otus_group_id) is None:
            otuid2ottid = {}
            ottid2otuid_list = {}
            self._otuid2ottid_byogid[otus_group_id] = otuid2ottid
            self._ottid2otuid_list_byogid[otus_group_id] = ottid2otuid_list
            otu_dict = self._otu_by_otug[otus_group_id]
            for otuid, otu in otu_dict.items():
                ottid = find_val_for_first_bf_l_meta(otu, 'ot:ottId')
                otuid2ottid[otuid] = ottid
                ottid2otuid_list.setdefault(ottid, []).append(otuid)
            return otuid2ottid, ottid2otuid_list
        return self._otuid2ottid_byogid[otus_group_id], self._ottid2otuid_list_byogid[otus_group_id]

    def _detect_multilabelled_tree(self,
                                   otus_group_id,
                                   tree_id,
                                   otuid2leaf):
        # See if there are any otus that we need to flag as occurring in a tree
        # multiple_times
        #
        pair = self._fill_otu_ottid_maps(otus_group_id)
        ottid2otuid_list = pair[1]
        dup_dict = {}
        nd_list = None
        for ottid, otuid_list in ottid2otuid_list.items():
            if isinstance(otuid_list, list) and len(otuid_list) > 1:
                if nd_list is None:
                    nd_list = []
                for otuid in otuid_list:
                    nd_id = otuid2leaf.get(otuid)
                    if nd_id is not None:
                        nd_list.append(nd_id)
                if len(nd_list) > 1:
                    dup_dict[ottid] = nd_list
                    nd_list = None
                else:
                    del nd_list[:]
        bt = self._dupottid_by_ogid_tree_id.setdefault(otus_group_id, {})
        bt[tree_id] = dup_dict

    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, vc):
        otus_group_list = nex_obj.get('otus')
        if otus_group_list and isinstance(otus_group_list, dict):
            otus_group_list = [otus_group_list]
        if not otus_group_list:
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['otus'])
            return False
        vc.push_context(_NEXEL.OTUS, (nex_obj, obj_nex_id))
        try:
            without_id = []
            og_tuple_list = []
            for og in otus_group_list:
                ogid = og.get('@id')
                if ogid is None:
                    without_id.append(og)
                else:
                    og_tuple_list.append((ogid, og))
            if without_id:
                self._error_event(_NEXEL.OTUS,
                                 obj=nex_obj,
                                 err_type=gen_MissingCrucialContentWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=without_id,
                                 key_list=['@id'])
                return False
            if not self._validate_otus_group_list(og_tuple_list, vc):
                return False
        finally:
            vc.pop_context()
        # and now the trees...
        trees_group_list = nex_obj.get('trees')
        if trees_group_list and isinstance(trees_group_list, dict):
            trees_group_list = [trees_group_list]
        if not trees_group_list:
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['trees'])
            return False
        vc.push_context(_NEXEL.TREES, (nex_obj, obj_nex_id))
        try:
            without_id = []
            tg_tuple_list = []
            for tg in trees_group_list:
                tgid = tg.get('@id')
                if tgid is None:
                    without_id.append(tg)
                else:
                    tg_tuple_list.append((tgid, tg))
            if without_id:
                self._error_event(_NEXEL.TREES,
                                 obj=without_id,
                                 err_type=gen_MissingCrucialContentWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=None,
                                 key_list=['@id'])
                return False
            return self._validate_trees_group_list(tg_tuple_list, vc)
        finally:
            vc.pop_context()

def construct_path_to_root(node, encountered_nodes, edge_by_target):
    n = node
    p = []
    s = set()
    while n:
        if n in s:
            return n, p
        if n in encountered_nodes:
            return None, []
        nid = n.get('@id')
        p.append(nid)
        s.add(nid)
        encountered_nodes.add(n)
        e = edge_by_target.get(n)
        src = None
        if e:
            src = e.get('@source')
        if src:
            n = src
        else:
            break
    return None, p
