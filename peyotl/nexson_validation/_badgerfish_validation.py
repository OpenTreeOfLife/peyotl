#!/usr/bin/env python
from peyotl.nexson_validation.helper import _NEXEL, errorReturn
from peyotl.nexson_validation.err_generator import gen_InvalidKeyWarning, \
                                                   gen_MissingCrucialContentWarning, \
                                                   gen_MissingMandatoryKeyWarning, \
                                                   gen_MultipleRootsWarning, \
                                                   gen_NodeWithMultipleParents, \
                                                   gen_NoRootWarning, \
                                                   gen_ReferencedIDNotFoundWarning, \
                                                   gen_RepeatedOTUWarning, \
                                                   gen_TreeCycleWarning, \
                                                   gen_WrongValueTypeWarning
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


    def _post_key_check_validate_otus_obj(self, og_nex_id, otus_group, vc):
        otu_dict = {}
        otu_list = otus_group.get('otu', [])
        if isinstance(otu_list, dict):
            otu_list = [otu_list]
        if not otu_list:
            return
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
                return errorReturn('lack of "@id" in "otu"')
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
            return errorReturn('bad "@otus" in trees group')
        tree_list = trees_group.get('tree', [])
        if isinstance(tree_list, dict):
            tree_list = [tree_list]
        elif not isinstance(tree_list, list):
            self._error_event(_NEXEL.TREES,
                             obj=trees_group,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tg_nex_id,
                             key_list=['tree'])
            return errorReturn('lack of "tree" in trees group')
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
                    return errorReturn('no "@id" in tree')
                if not self._validate_tree(t_nex_id,
                                           tree_obj,
                                           vc,
                                           otus_group_id=otus_el):
                    return False
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
            return errorReturn('no "node" in "trees"')
        edge_list = tree_obj.get('edge')
        if isinstance(edge_list, dict):
            edge_list = [edge_list]
        elif (not edge_list) or (not isinstance(edge_list, list)):
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['edge',])
            return errorReturn('no "edge" in tree')
        edge_id_list = [(i.get('@id'), i) for i in edge_list]
        valid = self._validate_edge_list(edge_id_list, vc)
        if not valid:
            return False
        node_id_obj_list = [(i.get('@id'), i) for i in node_list]
        valid = self._validate_node_list(node_id_obj_list, vc)
        if not valid:
            return False
        node_dict = {}
        for i in node_id_obj_list:
            nid, nd = i
            node_dict[nid] = nd
        missing_src = []
        missing_target = []
        for el in edge_id_list:
            e = el[1]
            sid = e.get('@source')
            tid = e.get('@target')
            if sid not in node_dict:
                missing_src.append(sid)
            if tid not in node_dict:
                missing_target.append(tid)
        if missing_src:
            self._error_event(_NEXEL.TREE,
                               obj=tree_obj,
                               err_type=gen_ReferencedIDNotFoundWarning,
                               anc=vc.anc_list,
                               obj_nex_id=tree_nex_id,
                               key_list=missing_src)
            return errorReturn('no "@source" in edge')
        if missing_target:
            self._error_event(_NEXEL.TREE,
                               obj=tree_obj,
                               err_type=gen_ReferencedIDNotFoundWarning,
                               anc=vc.anc_list,
                               obj_nex_id=tree_nex_id,
                               key_list=missing_target)
            return errorReturn('no "@target" in edge')
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
            #_LOG.debug('e=' + str(e))
            sid = e['@source']
            edge_by_source.setdefault(sid, []).append(e)
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
                return errorReturn('"@id" in node')
            if path_to_root:
                lowest_nodeid_set.add(path_to_root[-1])
                if first_lowest_node is None:
                    first_lowest_node = path_to_root[-1]
            is_flagged_as_leaf = find_val_for_first_bf_l_meta(nd, 'ot:isLeaf')
            ch_list = edge_by_source.get(nid)
            if ch_list is None:
                otu_id = nd.get('@otu')
                if otu_id is None:
                    vc.push_context(_NEXEL.NODE, (tree_obj, tree_nex_id))
                    try:
                        self._error_event(_NEXEL.NODE,
                                         obj=nd,
                                         err_type=gen_MissingCrucialContentWarning,
                                         anc=vc.anc_list,
                                         obj_nex_id=nid,
                                         key_list=['@otu',])
                        return errorReturn('"@otu" in leaf')
                    finally:
                        vc.pop_context()
                else:
                    if otu_id in otuid2leaf:
                        vc.push_context(_NEXEL.NODE, (tree_obj, tree_nex_id))
                        try:
                            self._error_event(_NEXEL.NODE,
                                             obj=nd,
                                             err_type=gen_RepeatedOTUWarning,
                                             anc=vc.anc_list,
                                             obj_nex_id=nid,
                                             key_list=[otu_id])
                            return errorReturn('repeated "@otu" in leaves')
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
            vc.push_context(_NEXEL.NODE, (tree_obj, tree_nex_id))
            try:
                #_LOG.debug('unflagged_leaves="{f}"'.format(f=unflagged_leaves))
                self._error_event(_NEXEL.NODE,
                                 obj=tree_obj,
                                 err_type=gen_MissingMandatoryKeyWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=unflagged_leaves,
                                 key_list=['ot:isLeaf'])
            finally:
                vc.pop_context()
        if nonleaves_with_leaf_flags:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_InvalidKeyWarning,
                             anc=vc.anc_list,
                             obj_nex_id=nonleaves_with_leaf_flags,
                             key_list=['ot:isLeaf'])
            return errorReturn('"ot:isLeaf" for internal')
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
            return errorReturn('multiple roots in a tree')

        root_node_id = first_lowest_node

        if root_node_id not in with_at_root_prop:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             node_id_list=with_at_root_prop.keys() + [root_node_id])
            return errorReturn('root without "@root"')
        elif len(with_at_root_prop) > 1:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             node_id_list=with_at_root_prop.keys())
            return errorReturn('Multiple nodes with "@root"')
        elif len(with_at_root_prop) == 0:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_NoRootWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id)
            return errorReturn('no node with "@root"')
        return True

    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, vc):
        otus_group_list = nex_obj.get('otus', [])
        if otus_group_list and isinstance(otus_group_list, dict):
            otus_group_list = [otus_group_list]
        if not isinstance(otus_group_list, list):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['otus'])
            return errorReturn('no "otus" in nexml')
        vc.push_context(_NEXEL.OTUS, (nex_obj, obj_nex_id))
        try:
            without_id = []
            og_tuple_list = []
            for og in otus_group_list:
                ogid = og.get('@id')
                if ogid is None:
                    without_id.append(None)
                else:
                    og_tuple_list.append((ogid, og))
            if without_id:
                self._error_event(_NEXEL.OTUS,
                                 obj=nex_obj,
                                 err_type=gen_MissingCrucialContentWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=None,
                                 key_list=['otus[*]/@id'])
                return errorReturn('otu without "@id"')
            if not self._validate_otus_group_list(og_tuple_list, vc):
                return False
        finally:
            vc.pop_context()
        # and now the trees...
        trees_group_list = nex_obj.get('trees', [])
        if trees_group_list and isinstance(trees_group_list, dict):
            trees_group_list = [trees_group_list]
        if not isinstance(trees_group_list, list):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['trees'])
            return errorReturn('No "trees" in nexml')
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
                return errorReturn('No "@id" in trees group"')
            if not self._validate_trees_group_list(tg_tuple_list, vc):
                return False
        finally:
            vc.pop_context()
        ogid2og = {}
        for og in otus_group_list:
            ogid = og.get('@id')
            ogid2og[ogid] = og
        if not find_val_for_first_bf_l_meta(nex_obj, 'ot:notIntendedForSynthesis'):
            cs = find_val_for_first_bf_l_meta(nex_obj, 'ot:candidateTreeForSynthesis')
            if cs:
                if not isinstance(cs, list):
                    tree_list = [cs]
                else:
                    tree_list = cs
            else:
                tree_list = []
                for tg in trees_group_list:
                    stree_list = tg.get('tree')
                    if not isinstance(stree_list, list):
                        stree_list = [stree_list]
                    tree_list.extend([i.get('@id') for i in stree_list])
            self._generate_ott_warnings(ogid2og, tree_list, (nex_obj, obj_nex_id), vc)
        return True

def construct_path_to_root(node, encountered_nodes, edge_by_target):
    nid = node.get('@id')
    p = []
    s = set()
    while nid:
        #_LOG.debug('node = "{node}"   n="{n}"'.format(node=str(node), n=str(n)))
        if nid in s:
            return nid, p
        if nid in encountered_nodes:
            return None, []
        p.append(nid)
        s.add(nid)
        encountered_nodes.add(nid)
        e = edge_by_target.get(nid)
        src = None
        if e:
            src = e.get('@source')
        if src:
            nid = src
        else:
            break
    return None, p
