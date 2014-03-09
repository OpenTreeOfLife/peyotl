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

class BadgerFishValidationAdaptor(NexsonValidationAdaptor):
    def __init__(self, obj, logger):
        NexsonValidationAdaptor.__init__(self, obj, logger)

    def _post_key_check_validate_otus_obj(self, og_nex_id, otus_group, vc):
        d = {}
        self._otu_by_otug[og_nex_id] = d
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
                d[oid] = otu
            if without_id:
                self._error_event(_NEXEL.NEXML,
                                 obj=without_id,
                                 err_type=gen_MissingCrucialContentWarning,
                                 anc=vc.anc_list,
                                 key_list=['@id'])
                return False
            return self._validate_otu_group_list(otu_tuple_list, vc)
        except:
            v.pop_context()
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
                             obj=tree_obj,
                             err_type=gen_MissingCrucialContentWarning,
                             anc=vc.anc_list,
                             obj_nex_id=tg_nex_id,
                             key_list=['tree'])
            return False
        for tree_obj in tree_list:
            t_nex_id = tree.get('@id')
            vc.push_context(_NEXEL.TREE, (tree_obj, None))
            try:
                if t_nex_id is None:
                    self._error_event(_NEXEL.TREE,
                                  obj=tree_obj,
                                  err_type=gen_MissingCrucialContentWarning,
                                  anc=vc.anc_list,
                                  obj_nex_id=tg_nex_id,
                                  key_list=['@id'])
                    return False
                if not self._validate_tree(t_nex_id, tree_obj, vc):
                    return True
            finally:
                vc.pop_context()
        return True



        d = {}
        self._otu_by_otug[og_nex_id] = d
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
                d[oid] = otu
            if without_id:
                self._error_event(_NEXEL.NEXML,
                                 obj=without_id,
                                 err_type=gen_MissingCrucialContentWarning,
                                 anc=vc.anc_list,
                                 key_list=['@id'])
                return False
            return self._validate_otu_group_list(otu_tuple_list, vc)
        except:
            v.pop_context()
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
                                 obj=without_id,
                                 err_type=gen_MissingCrucialContentWarning,
                                 anc=vc.anc_list,
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
                                 key_list=['@id'])
                return False
            return self._validate_trees_group_list(tg_tuple_list, vc)
        finally:
            vc.pop_context()
