#!/usr/bin/env python
'''Simple manipulations of data structure in peyotl
'''
from peyotl.nexson_syntax import BY_ID_HONEY_BADGERFISH, \
                                 convert_nexson_format, \
                                 detect_nexson_version

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
        1. merges trees elements 2 -... into the first trees element.,
        2. merges otus elements 2 - ... into the first otus element.
        3. if there is no ot:originalLabel field for any otu,
            it sets that field based on @label and deletes @label
        3. merges an otu elements using the rule:
              A. treat (ottId, originalLabel) as a key
              B. If otu objects in subsequent trees match originalLabel and
                have a matching or absent ot:ottId, then they are merged into
                the same OTUs
              C. No two leaves of a tree may share an otu (though otu should
                be shared across different trees)

        4. correct object references to deleted entities.
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
    retained_otu_orig = {}
    retained_otu_orig_label = {}
    if len(otus_group_order) > 0:
        otus_group_by_id = nexson['treesById']
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
                m = retained_otu_orig.setdefault(key, [])
                m.append(t)
                if orig is not None:
                    m = retained_otu_orig_label.setdefault((None, orig), [])
                    m.append(t)
    if len(otus_group_order) > 1:
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
                    mlist = retained_otu_orig.get(key)
                    if mlist is not None:
                        for m in mlist:
                            if m not in used_matches:
                                match_otu = m
                                break
                    mlist = retained_otu_orig_label.get((None, orig))
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
                        m = retained_otu_orig.setdefault(key, [])
                        m.append(t)
                        if orig is not None:
                            m = retained_otu_orig_label.setdefault((None, orig), [])
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