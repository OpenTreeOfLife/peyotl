#!/usr/bin/env python
'''Simple manipulations of data structure in peyotl
'''
from peyotl.nexson_syntax import BY_ID_HONEY_BADGERFISH, \
                                 convert_nexson_format, \
                                 detect_nexson_version, \
                                 _is_by_id_hbf

def count_num_trees(nexson, nexson_version=None):
    if nexson_version is None:
        nexson_version = detect_nexson_version(nexson)
    nex = nexson.get('nex:nexml') or nexson['nexml']
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
def label_to_original_label_otu_by_id(otu_by_id):
    '''Takes a v1.2 otuById dict and, for every otu,
    checks if ot:originalLabel exists. If it does not,
    but @label does, then ot:originalLabel is set to
    @label and @label is deleted.
    '''
    for val in otu_by_id.values():
        orig = val.get('ot:originalLabel')
        if orig is None:
            label = val.get('@label')
            if label:
                del val['@label']
                val['ot:originalLabel'] = label

def merge_otus_and_trees(nexson):
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
                will be no way of separating them during OTU mapping.

        5. correct object references to deleted entities.

    This function is used to patch up NexSONs created by multiple imports, hence the 
    substitution of '@label' for 'ot:originalLabel'. Ids are arbitrary for imports from
    non-nexml tools, so matching is done based on names. This should mimic the behavior
    of the analysis tools that produced the trees (for most/all such tools unique names
    constitute unique OTUs).
    '''
    orig_version = detect_nexson_version(nexson)
    convert_nexson_format(nexson, BY_ID_HONEY_BADGERFISH)

    replaced_otu_id_by_group = {}
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
        retained_og = otus_group_by_id[retained_tgi]
        otu_by_id = retained_og.get('otuById', {})
        label_to_original_label_otu_by_id(otu_by_id)
        replaced_otu_id_by_group[retained_ogi] = {}
        for oid, otu in otu_by_id.items():
            ottid = otu.get('^ot:ottId')
            orig = otu.get('ot:originalLabel')
            key = (ottid, orig)
            if key != (None, None):
                t = (oid, otu)
                m = retained_mapped2otu.setdefault(key, [])
                m.append(t)
                if orig is not None:
                    m = retained_orig2otu.setdefault(orig, [])
                    m.append(t)
    # For each of the other otus elements, we:
    #   1. assure that originalLabel is filled in
    for ogi in otus_group_order[1:]:
        og = otus_group_by_id[ogi]
        otu_by_id = og.get('otuById', {})
        label_to_original_label_otu_by_id(otu_by_id)
        replaced_otu = {}
        used_matches = set()
        for oid, otu in otu_by_id.items():
            ottid = otu.get('^ot:ottId')
            orig = otu.get('ot:originalLabel')
            key = (ottid, orig)
            if key == (None, None):
                retained_og[oid] = otu
            else:
                match_otu = None
                mlist = retained_mapped2otu.get(key)
                if mlist is not None:
                    for m in mlist:
                        if m not in used_matches:
                            match_otu = m
                            break
                mlist = retained_orig2otu.get(orig)
                if (match_otu is None) and (mlist is not None):
                    for m in mlist:
                        if m not in used_matches:
                            match_otu = m
                            break
                if match_otu is not None:
                    replaced_otu[oid] = match_otu
                    _merge_otu_do_not_fix_references(match_otu[1], otu)
                else:
                    assert(oid not in retained_og)
                    retained_og[oid] = otu
                    t = (oid, otu)
                    m = retained_mapped2otu.setdefault(key, [])
                    m.append(t)
                    if orig is not None:
                        m = retained_orig2otu.setdefault(orig, [])
                        m.append(t)
        replaced_otu_id_by_group[ogi] = replaced_otu

    deleted_trees_group_ids = set()
    trees_group_order = nexson.get('^ot:treesElementOrder', [])
    if len(trees_group_order) > 0:
        trees_group_by_id = nexson['treesById']
        retained_tgi = trees_group_order[0]
        retained_tg = trees_group_by_id[retained_tgi]
    if len(trees_group_order) > 1:
        for tgi in trees_group_order[1:]:
            tg = trees_group_by_id[tgi]

    convert_nexson_format(nexson, orig_version)
    return nexson