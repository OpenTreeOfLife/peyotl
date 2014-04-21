#!/usr/bin/env python
from peyotl.nexson_validation.helper import _NEXEL, errorReturn
from peyotl.nexson_validation.schema import check_raw_dict
from peyotl.nexson_validation.err_generator import gen_MissingCrucialContentWarning, \
                                                   gen_MultipleRootsWarning, \
                                                   gen_NodeWithMultipleParents, \
                                                   gen_NoRootWarning, \
                                                   gen_ReferencedIDNotFoundWarning, \
                                                   gen_RepeatedIDWarning, \
                                                   gen_RepeatedOTUWarning, \
                                                   gen_UnreachableNodeWarning, \
                                                   gen_WrongValueTypeWarning
from peyotl.nexson_validation._validation_base import NexsonValidationAdaptor
from peyotl.nexson_syntax.helper import BY_ID_HONEY_BADGERFISH
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

class ByIdHBFValidationAdaptor(NexsonValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)
        self._syntax_version = BY_ID_HONEY_BADGERFISH
    def _post_key_check_validate_otus_obj(self, og_nex_id, otus_group, vc):
        otu_obj = otus_group.get('otuById', {})
        if not isinstance(otu_obj, dict):
            self._error_event(_NEXEL.OTUS,
                             obj=otus_group,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             obj_nex_id=og_nex_id,
                             key_list=['otuById'])
            return errorReturn('no "otuById" in otus group')
        self._otu_group_by_id[og_nex_id] = otus_group
        vc.push_context(_NEXEL.OTU, (otus_group, og_nex_id))
        try:
            not_dict_otu = []
            ndo_id_list = []
            otu_id_obj_list = []
            for id_obj_pair in otu_obj.items():
                if not isinstance(id_obj_pair[1], dict):
                    r = check_raw_dict(id_obj_pair[1], otus_group, None, vc)
                    assert r[0] is False
                    t = r[1]
                    not_dict_otu.append(t)
                    ndo_id_list.append(id_obj_pair[0])
                else:
                    otu_id_obj_list.append(id_obj_pair)
            if not_dict_otu:
                self._error_event(_NEXEL.OTU,
                                 obj=otu_obj,
                                 err_type=gen_WrongValueTypeWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=ndo_id_list,
                                 key_val_type_list=[not_dict_otu])
                return errorReturn('otu is wrong type')
            r = self._validate_otu_list(otu_id_obj_list, vc)
            if r:
                self._otu_by_otug[og_nex_id] = otu_obj
            return r
        finally:
            vc.pop_context()

    def _post_key_check_validate_tree_group(self, tg_nex_id, tree_group_obj, vc):
        tree_id_order = tree_group_obj.get('^ot:treeElementOrder', [])
        tree_by_id = tree_group_obj.get('treeById', {})
        if (not isinstance(tree_by_id, dict)) \
            or (not isinstance(tree_id_order, list)):
            self._error_event(_NEXEL.TREES,
                             obj=tree_group_obj,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tg_nex_id,
                             key_list=['treeById', '^ot:treeElementOrder'])
            return errorReturn('no "treeById" in trees group')
        if ((not tree_by_id) and tree_id_order) or ((not tree_id_order) and tree_by_id):
            self._error_event(_NEXEL.TREES,
                             obj=tree_group_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tg_nex_id,
                             key_list=['treeById', '^ot:treeElementOrder'])
            return errorReturn('no "treeById" in trees group')
        otus_el = tree_group_obj.get('@otus')
        if otus_el not in self._otu_group_by_id:
            self._error_event(_NEXEL.TREES,
                               obj=tree_group_obj,
                               err_type=gen_ReferencedIDNotFoundWarning,
                               anc=vc.anc_list,
                               obj_nex_id=tg_nex_id,
                               key_list=[otus_el])
            return errorReturn('no "@otus" in trees group')
        for t_nex_id, tree_obj in tree_by_id.items():
            vc.push_context(_NEXEL.TREE, (tree_obj, t_nex_id))
            try:
                if not self._validate_tree(t_nex_id, tree_obj, vc, otus_group_id=otus_el):
                    return False
            finally:
                vc.pop_context()
        return True

    def _post_key_check_validate_tree(self,
                                      tree_nex_id,
                                      tree_obj,
                                      vc,
                                      otus_group_id=None):
        #pylint: disable=R0914
        node_by_id = tree_obj.get('nodeById')
        edge_by_source = tree_obj.get('edgeBySourceId')
        root_node_id = tree_obj.get('^ot:rootNodeId')
        if (not node_by_id) or (not isinstance(node_by_id, dict)):
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['nodeById',])
            return errorReturn('no "nodeById" in tree')
        if (not edge_by_source) or (not isinstance(edge_by_source, dict)):
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['edgeBySourceId',])
            return errorReturn('no "edgeBySourceId" in tree')
        if (not isinstance(root_node_id, str)) and (not isinstance(root_node_id, unicode)):
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=['^ot:rootNodeId',])
            return errorReturn('no "^ot:rootNodeId" in tree')
        edge_dict = {}
        edge_by_target = {}
        internal_nodes = []
        if otus_group_id is None:
            tree_group = vc.anc_list[-1][1]
            otus_group_id = tree_group.get('@otus')

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
            if unreachable:
                self._error_event(_NEXEL.TREE,
                                 obj=tree_obj,
                                 err_type=gen_UnreachableNodeWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=tree_nex_id,
                                 key_list=unreachable)
                return errorReturn('unreachable node in tree tree')
            if not_in_node_by_id:
                self._error_event(_NEXEL.TREE,
                                 obj=tree_obj,
                                 err_type=gen_ReferencedIDNotFoundWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=tree_nex_id,
                                 key_list=not_in_node_by_id)
                return errorReturn('referenced node id not in "nodeById" in tree')
        if bad_node_ref:
            bad_node_ref.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=bad_node_ref)
            return errorReturn('referenced parent node not in "nodeById" in tree')
        if missing_target:
            missing_target.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=missing_target)
            return errorReturn('no "@target" in edge')
        if repeated_target:
            repeated_target.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_NodeWithMultipleParents,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             node_id_list=repeated_target)
            return errorReturn('same node used as "@target" for different edges')
        if repeated_edge_id:
            repeated_edge_id.sort()
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_RepeatedIDWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             key_list=repeated_edge_id)
            return errorReturn('edge "@id" repeated')
        node_set = set(edge_by_target.keys())
        internal_node_set = set(edge_by_source.keys())
        leaf_set = node_set - internal_node_set
        leaves = [(i, node_by_id[i]) for i in leaf_set]
        if not self._validate_leaf_list(leaves, vc):
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
                             obj_nex_id=tree_nex_id,
                             node_id_list=with_at_root_prop.keys())
            return errorReturn('multiple "@root" nodes')
        if len(with_at_root_prop) == 0:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_NoRootWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id)
            return errorReturn('No node labelled as "@root"')
        if root_node_id not in with_at_root_prop:
            self._error_event(_NEXEL.TREE,
                             obj=tree_obj,
                             err_type=gen_MultipleRootsWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tree_nex_id,
                             node_id_list=with_at_root_prop.keys() + [root_node_id])
            return errorReturn('root node not labelled as root')
        if not self._validate_internal_node_list(internal_nodes, vc):
            return False
        edges = [i for i in edge_dict.items()]
        if not self._validate_edge_list(edges, vc):
            return False
        otuid2leaf = {}
        for nd_id, nd in leaves:
            otuid = nd['@otu']
            if otuid in otuid2leaf:
                vc.push_context(_NEXEL.LEAF_NODE, (tree_obj, tree_nex_id))
                try:
                    self._error_event(_NEXEL.LEAF_NODE,
                                     obj=nd,
                                     err_type=gen_RepeatedOTUWarning,
                                     anc=vc.anc_list,
                                     obj_nex_id=nd_id,
                                     key_list=[otuid])
                    return errorReturn('Repeated "@otu" id')
                finally:
                    vc.pop_context()
            otuid2leaf[otuid] = nd_id
        self._detect_multilabelled_tree(otus_group_id=otus_group_id,
                                        tree_id=tree_nex_id,
                                        otuid2leaf=otuid2leaf)

    def _post_key_check_validate_nexml_obj(self, nex_obj, obj_nex_id, vc):
        otus = nex_obj.get('otusById', {})
        otus_order_list = nex_obj.get('^ot:otusElementOrder', [])
        if not isinstance(otus, dict) or (otus_order_list and (not otus)):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['otusById'])
            return errorReturn('Missing "otusById"')
        if (not isinstance(otus_order_list, list)) or ((not otus_order_list) and otus):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_WrongValueTypeWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['^ot:otusElementOrder'])
            return errorReturn('Missing "^ot:otusElementOrder"')
        otus_group_list = []
        missing_ogid = []
        not_dict_og = []
        for ogid in otus_order_list:
            og = otus.get(ogid)
            if og is None:
                missing_ogid.append(ogid)
            elif not isinstance(og, dict):
                r = check_raw_dict(og, otus, ogid, vc)
                assert r[0] is False
                t = r[1]
                not_dict_og.append(t)
            else:
                otus_group_list.append((ogid, og))
        if missing_ogid:
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=missing_ogid)
            return errorReturn('Missing "@id" for otus group')
        vc.push_context(_NEXEL.OTUS, (nex_obj, obj_nex_id))
        try:
            if not_dict_og:
                self._error_event(_NEXEL.OTUS,
                                 obj=otus,
                                 err_type=gen_WrongValueTypeWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=None,
                                 key_val_type_list=[not_dict_og])
                return errorReturn('Otus objects of the wrong type of object')
            if not self._validate_otus_group_list(otus_group_list, vc):
                return False
        finally:
            vc.pop_context()
        # and now the trees...
        trees = nex_obj.get('treesById')
        trees_order_list = nex_obj.get('^ot:treesElementOrder')
        if (not isinstance(trees, dict)) or ((not trees) and trees_order_list):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['treesById'])
            return errorReturn('Missing "treesById"')
        if (not isinstance(trees_order_list, list)) or ((not trees_order_list) and trees):
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=['^ot:treesElementOrder'])
            return errorReturn('Missing "^ot:treesElementOrder"')
        trees_group_list = []
        missing_tgid = []
        not_dict_tg = []
        for tgid in trees_order_list:
            tg = trees.get(tgid)
            if tg is None:
                missing_tgid.append(tgid)
            elif not isinstance(tg, dict):
                r = check_raw_dict(tg, trees, tgid, vc)
                assert r[0] is False
                t = r[1]
                not_dict_tg.append(t)
            else:
                trees_group_list.append((tgid, tg))
        if missing_tgid:
            self._error_event(_NEXEL.NEXML,
                             obj=nex_obj,
                             err_type=gen_ReferencedIDNotFoundWarning,
                             anc=vc.anc_list,
                             obj_nex_id=obj_nex_id,
                             key_list=missing_tgid)
            return errorReturn('Missing trees group id')
        vc.push_context(_NEXEL.TREES, (nex_obj, obj_nex_id))
        try:
            if not_dict_tg:
                self._error_event(_NEXEL.TREES,
                                 obj=trees,
                                 err_type=gen_WrongValueTypeWarning,
                                 anc=vc.anc_list,
                                 obj_nex_id=None,
                                 key_val_type_list=[not_dict_tg])
                return errorReturn('Trees element of the wrong type')
            if not self._validate_trees_group_list(trees_group_list, vc):
                return False
        finally:
            vc.pop_context()
        if not nex_obj.get('ot:notIntendedForSynthesis'):
            cs = nex_obj.get('ot:candidateTreeForSynthesis')
            if cs:
                if not isinstance(cs, list):
                    tree_list = [cs]
                else:
                    tree_list = cs
            else:
                tree_list = []
                for tg in trees.values():
                    tbi = tg.get('treeById', {})
                    tree_list.extend(tbi.keys())
            self._generate_ott_warnings(otus, tree_list, (nex_obj, obj_nex_id), vc)
        return True
