#!/usr/bin/env python
from peyotl import write_as_json
from peyotl.nexson_syntax.helper import add_literal_meta, \
                                        find_val_literal_meta_first
SYNTAX_VERSION = '0.0.0'
def _rec_resource_meta(blob, k):
    if k == 'meta' and isinstance(blob, dict):
        if blob.get('@xsi:type') == 'nex:ResourceMeta':
            if blob.get('@rel') is None:
                p = blob.get('@property')
                if p is not None:
                    del blob['@property']
                    blob['@rel'] = p
    if isinstance(blob, list):
        for i in blob:
            _rec_resource_meta(i, k)
    else:
        for inner_k, v in blob.items():
            if isinstance(v, list) or isinstance(v, dict):
                _rec_resource_meta(v, inner_k)

def _coerce_boolean(blob, k):
    '''Booleans emitted as "true" or "false"
    for "@root" and "ot:isLeaf" meta
    '''
    if isinstance(blob, dict):
        if k == 'meta':
            if blob.get('@property') == 'ot:isLeaf':
                v = blob.get('$')
                try:
                    if v.lower() == "true":
                        blob['$'] = True
                    elif v.lower == "false":
                        blob['$'] = False
                except:
                    pass
        else:
            r = blob.get('@root')
            if r is not None:
                try:
                    if r.lower() == "true":
                        blob['@root'] = True
                    elif r.lower == "false":
                        blob['@root'] = False
                except:
                    pass
        for inner_k, v in blob.items():
            if isinstance(v, list) or isinstance(v, dict):
                _coerce_boolean(v, inner_k)
    elif isinstance(blob, list):
        for i in blob:
            _coerce_boolean(i, k)

def _move_ott_taxon_name_to_otu(obj):
    nex = obj['nexml']
    ogl = nex['otus']
    tree_group_list = nex['trees']
    if not tree_group_list:
        return
    ogi_to_oid2otu = {}
    if not isinstance(ogl, list):
        ogl = [ogl]
    if not isinstance(tree_group_list, list):
        tree_group_list = [tree_group_list]
    for og in ogl:
        ogi = og['@id']
        od = {}
        for otu in og['otu']:
            oi = otu['@id']
            od[oi] = otu
        ogi_to_oid2otu[ogi] = od
    for tg in tree_group_list:
        ogi = tg['@otus']
        oid2otu = ogi_to_oid2otu[ogi]
        for tree in tg['tree']:
            for node in tree['node']:
                m = node.get('meta')
                if not m:
                    continue
                to_move = None
                if isinstance(m, dict):
                    if m.get('@property') == "ot:ottTaxonName":
                        to_move = m
                        del node['meta']
                else:
                    assert isinstance(m, list)
                    ind_to_del = None
                    for n, ottnm in enumerate(m):
                        if ottnm.get('@property') == "ot:ottTaxonName":
                            to_move = ottnm
                            ind_to_del = n
                            break
                    if ind_to_del:
                        m.pop(ind_to_del)
                if to_move:
                    oid = node['@otu']
                    otu = oid2otu[oid]
                    om = otu.get('meta')
                    if om is None:
                        otu['meta'] = to_move
                    elif isinstance(om, dict):
                        if om.get('@property') != "ot:ottTaxonName":
                            otu['meta'] = [om, to_move]
                    else:
                        assert isinstance(om, list)
                        found = False
                        for omel in om:
                            if omel.get('@property') == "ot:ottTaxonName":
                                found = True
                                break
                        if not found:
                            om.append(to_move)


def _move_otu_at_label_properties(obj):
    nex = obj['nexml']
    ogl = nex['otus']
    if not isinstance(ogl, list):
        ogl = [ogl]
    for og in ogl:
        for otu in og['otu']:
            ol = find_val_literal_meta_first(otu, 'ot:originalLabel', SYNTAX_VERSION)
            assert ol is not None
            label_att = otu.get('@label')
            if label_att is not None:
                del otu['@label']
                if label_att != ol:
                    ml = find_val_literal_meta_first(otu, 'ot:ottTaxonName', SYNTAX_VERSION)
                    if (not ml) or (ml != label_att):
                        add_literal_meta(otu, 'ot:altLabel', label_att, SYNTAX_VERSION)

def workaround_phylografter_export_diffs(obj, out):
    _rec_resource_meta(obj, 'root')
    _coerce_boolean(obj, 'root')
    _move_ott_taxon_name_to_otu(obj)
    _move_otu_at_label_properties(obj)
    write_as_json(obj, out)
