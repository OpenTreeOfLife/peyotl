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
        for trees_group_id in nex.get('^ot:treesElementOrder', []):
            trees_group = trees_group_by_id[trees_group_id]
            tree_by_id = trees_group['treeById']
            ti_order = trees_group['^ot:treeElementOrder']
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
                                match_otu = m
                                break
                    if match_otu is None:
                        mlist = retained_orig2otu.get(orig, [])
                        for m in mlist:
                            if m[0] not in used_matches:
                                match_otu = m
                                break
                    if match_otu is not None:
                        id_to_replace_id[oid] = match_otu[0]
                        used_matches = match_otu[0]
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
