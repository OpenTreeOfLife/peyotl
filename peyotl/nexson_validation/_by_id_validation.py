#!/usr/bin/env python
from peyotl.nexson_validation.helper import SeverityCodes, _NEXEL
from peyotl.nexson_validation.schema import add_schema_attributes, check_raw_dict
from peyotl.nexson_validation.err_generator import factory2code, \
                                                   gen_MissingCrucialContentWarning, \
                                                   gen_MissingExpectedListWarning, \
                                                   gen_MissingMandatoryKeyWarning, \
                                                   gen_MissingOptionalKeyWarning, \
                                                   gen_MultipleRootsWarning, \
                                                   gen_NoRootWarning, \
                                                   gen_ReferencedIDNotFoundWarning, \
                                                   gen_RepeatedIDWarning, \
                                                   gen_UnparseableMetaWarning, \
                                                   gen_UnrecognizedKeyWarning, \
                                                   gen_WrongValueTypeWarning
from peyotl.nexson_syntax.helper import get_nexml_el, \
                                        extract_meta, \
                                        _add_value_to_dict_bf, \
                                        _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf
from peyotl.nexson_syntax import detect_nexson_version
from peyotl.nexson_validation._validation_base import NexsonValidationAdaptor
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

class ByIdHBFValidationAdaptor(NexsonValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)
    def _post_key_check_validate_otus_obj(self, og_nex_id, otus_group, vc):
        otu_obj = otus_group.get('otuById')
        if (not otu_obj) or (not isinstance(otu_obj, dict)):
            self._error_event(_NEXEL.OTUS,
                             obj=otus_group,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=og_nex_id,
                             key_list=['otuById'])
            return False
        self._otu_group_by_id[og_nex_id] = otus_group
        vc.push_context(_NEXEL.OTU, (otus_group, og_nex_id))
        try:
            not_dict_otu = []
            otu_id_obj_list = []
            for id_obj_pair in otu_obj.items():
                if not isinstance(id_obj_pair[1], dict):
                    r = check_raw_dict(id_obj_pair[1], otus_group, None, vc)
                    assert(r[0] is False)
                    t = r[1]
                    not_dict_otu.append(t)
                else:
                    otu_id_obj_list.append(id_obj_pair)
            if not_dict_otu:
                self._error_event(_NEXEL.OTU,
                                 obj=otu_obj,
                                 err_type=gen_WrongValueTypeWarning,
                                 anc=vc.anc_list,
                                 key_val_type_list=[not_dict_otu])
                return False
            return self._validate_otu_group_list(otu_id_obj_list, vc)
        finally:
            vc.pop_context()
    def _post_key_check_validate_tree_group(self, tg_nex_id, tree_group_obj, vc):
        tree_id_order = tree_group_obj.get('^ot:treeElementOrder')
        tree_by_id = tree_group_obj.get('treeById')
        if (not tree_by_id) or (not isinstance(tree_by_id, dict)) \
            or (not tree_id_order) or (not isinstance(tree_id_order, list)):
            self._error_event(_NEXEL.TREES,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tg_nex_id,
                             key_list=['treeById', '^ot:treeElementOrder'])
            return False
        otus_el = tree_group_obj.get('@otus')
        if otus_el not in self._otu_group_by_id:
            self._error_event(_NEXEL.TREES,
                               obj=tree_group_obj,
                               err_type=gen_ReferencedIDNotFoundWarning,
                               anc=vc.anc_list,
                               key_list=[otus_el])
            return False
        for t_nex_id, tree_obj in tree_by_id.items():
            vc.push_context(_NEXEL.TREE, (tree_obj, t_nex_id))
            try:
                self._validate_tree(t_nex_id, tree_obj, vc)
            finally:
                vc.pop_context()

    def _post_key_check_validate_tree(self, tree_nex_id, tree_obj, vc):
        node_by_id = tree_obj.get('nodeById')
        edge_by_source = tree_obj.get('edgeBySourceId')
        root_node_id = tree_obj.get('^ot:rootNodeId')
        if (not node_by_id) or (not isinstance(node_by_id, dict)):
            self._error_event(_NEXEL.TREES,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['nodeById',])
            return False
        if (not edge_by_source) or (not isinstance(edge_by_source, dict)):
            self._error_event(_NEXEL.TREES,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['edgeBySourceId',])
            return False
        if (not isinstance(root_node_id, str)) and (not isinstance(root_node_id, unicode)):
            self._error_event(_NEXEL.TREES,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['^ot:rootNodeId',])
            return False
        edge_dict = {}
        edge_by_target = {}
        internal_nodes = []
        fatal = False

        bad_node_ref = []
        repeated_edge_id = []
        missing_target = []
        repeated_target = []
        reachable_nodes = set()
        for par_node_id, edge_by_id in edge_by_source.items():
            if par_node_id not in node_by_id:
                bad_node_ref.append(par_node_id)
            else:
                reachable_nodes.add(par_node_id)
                for edge_id, edge in edge_by_id.items():
                    if edge_id in edge_dict:
                        repeated_edge_id.append(edge_id)
                    else:
                        edge_dict[edge_id] = edge
                        try:
                            t = edge.get('@target')
                        except:
                            t = None
                        if t is None:
                            missing_target.append(edge_id)
                        elif t in edge_by_target:
                            repeated_target.append(t)
                        else:
                            edge_by_target[t] = edge
                            reachable_nodes.add(t)
        node_set = set(node_by_id.keys())
        if node_set != reachable_nodes:
            unreachable = list(node_set - reachable_nodes)
            unreachable.sort()
            not_in_node_by_id = list(reachable_nodes - node_set)
            not_in_node_by_id.sort()
            fatal = True
            if unreachable:
                self._error_event(_NEXEL.TREE,
                                 obj=tree_obj,
                                 err_type=gen_UnreachableNodeWarning,
                                 anc=vc.anc_list,
                                 key_list=unreachable)
            if not_in_node_by_id:
                self._error_event(_NEXEL.TREE,
                                 obj=tree_obj,
                                 err_type=gen_ReferencedIDNotFoundWarning,
                                 anc=vc.anc_list,
                                 key_list=not_in_node_by_id)
        if bad_node_ref:
            fatal = True
            bad_node_ref.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             key_list=bad_node_ref)
        if missing_target:
            fatal = True
            missing_target.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             key_list=missing_target)
        if repeated_target:
            fatal = True
            repeated_target.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_NodeWithMultipleParents,
                             anc=vc.anc_list,
                             node_id_list=repeated_target)
        if repeated_edge_id:
            fatal = True
            repeated_edge_id.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_RepeatedIDWarning,
                             anc=vc.anc_list,
                             key_list=repeated_edge_id)
        if fatal:
            return False
        node_set = set(edge_by_target.keys())
        internal_node_set = set(edge_by_source.keys())
        leaf_set = node_set - internal_node_set
        leaves = [(i, node_by_id[i]) for i in leaf_set]
        valid = self._validate_leaf_list(leaves, vc)
        if not valid:
            return False
        internal_nodes = [(i, node_by_id[i]) for i in internal_node_set]
        with_at_root_prop = {}
        for nid, n_obj in internal_nodes:
            if n_obj.get('@root'):
                with_at_root_prop[nid] = n_obj
        if len(with_at_root_prop) > 1:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             node_id_list=with_at_root_prop.keys())
            return False
        if len(with_at_root_prop) == 0:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_NoRootWarning,
                             anc=vc.anc_list)
            return False
        if root_node_id not in with_at_root_prop:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             node_id_list=with_at_root_prop.keys() + [root_node_id])
            return False
        valid = self._validate_internal_node_list(internal_nodes, vc)
        if not valid:
            return False
        edges =[i for i in edge_dict.items()]
        return self._validate_edge_list(edges, vc)

    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, vc):
        otus = nex_obj.get('otusById')
        otus_order_list = nex_obj.get('^ot:otusElementOrder')
        if (not otus) or (not isinstance(otus, dict)) \
            or (not otus_order_list) or (not isinstance(otus_order_list, list)):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['otusById', '^ot:otusElementOrder'])
            return False
        otus_group_list = []
        missing_ogid = []
        not_dict_og = []
        for ogid in otus_order_list:
            og = otus.get(ogid)
            if og is None:
                missing_ogid.append(ogid)
            elif not isinstance(og, dict):
                r = check_raw_dict(og, otus, ogid, vc)
                assert(r[0] is False)
                t = r[1]
                not_dict_og.append(t)
            else:
                otus_group_list.append((ogid, og))
        if missing_ogid:
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             key_list=missing_ogid)
            return False
        vc.push_context(_NEXEL.OTUS, (nex_obj, obj_nex_id))
        try:
            if not_dict_og:
                self._error_event(_NEXEL.OTUS,
                                 obj=otus,
                                 err_type=gen_WrongValueTypeWarning,
                                 anc=vc.anc_list,
                                 key_val_type_list=[not_dict_og])
                return False
            if not self._validate_otus_group_list(otus_group_list, vc):
                return False
        finally:
          vc.pop_context()
        # and now the trees...
        trees = nex_obj.get('treesById')
        trees_order_list = nex_obj.get('^ot:treesElementOrder')
        if (not trees) or (not isinstance(trees, dict)) \
            or (not trees_order_list) or (not isinstance(trees_order_list, list)):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['treesById', '^ot:treesElementOrder'])
            return False
        trees_group_list = []
        missing_tgid = []
        not_dict_tg = []
        for tgid in trees_order_list:
            tg = trees.get(tgid)
            if tg is None:
                missing_tgid.append(tgid)
            elif not isinstance(tg, dict):
                r = check_raw_dict(tg, trees, tgid, vc)
                assert(r[0] is False)
                t = r[1]
                not_dict_tg.append(t)
            else:
                trees_group_list.append((tgid, tg))
        if missing_tgid:
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             key_list=missing_tgid)
            return False
        vc.push_context(_NEXEL.TREES, (nex_obj, obj_nex_id))
        try:
            if not_dict_tg:
                self._error_event(_NEXEL.treeS,
                                 obj=trees,
                                 err_type=gen_WrongValueTypeWarning,
                                 anc=vc.anc_list,
                                 key_val_type_list=[not_dict_tg])
                return False
            if not self._validate_trees_group_list(trees_group_list, vc):
                return False
        finally:
          vc.pop_context()
