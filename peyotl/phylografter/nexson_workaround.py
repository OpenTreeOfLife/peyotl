#!/usr/bin/env python
from peyotl import get_logger
from peyotl import write_as_json
from peyotl.nexson_syntax.helper import add_literal_meta, \
                                        detect_nexson_version, \
                                        find_val_literal_meta_first
_LOG = get_logger(__name__)
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
    if 'otus' in nex:
        syntax=SYNTAX_VERSION

        ogl = nex['otus']
        if not isinstance(ogl, list):
            ogl = [ogl]
        for og in ogl:
            for otu in og['otu']:
                _move_label_properties_for_otu(otu, syntax)
    else:
        syntax = detect_nexson_version(obj)
        assert 'otusById' in nex
        for otus_group in nex.get('otusById', {}).values():
            assert 'otuById' in otus_group
            for otu in otus_group.get('otuById', {}).values():
                _move_label_properties_for_otu(otu, syntax)
def _move_label_properties_for_otu(otu, syntax_version):
    ol = find_val_literal_meta_first(otu, 'ot:originalLabel', syntax_version)
    assert ol is not None
    label_att = otu.get('@label')
    if label_att is not None:
        del otu['@label']
        if label_att != ol:
            ml = find_val_literal_meta_first(otu, 'ot:ottTaxonName', syntax_version)
            if (not ml) or (ml != label_att):
                add_literal_meta(otu, 'ot:altLabel', label_att, syntax_version)

def _add_defaults(obj):
    nex = obj['nexml']
    if '^ot:annotationEvents' not in nex:
        nex['^ot:annotationEvents'] = {'annotation': []}
    if '^ot:candidateTreeForSynthesis' not in nex:
        nex['^ot:candidateTreeForSynthesis'] = []
    if '^ot:messages' not in nex:
        nex['^ot:messages'] = {'message': []}
    if '^ot:tag' not in nex:
        nex['^ot:tag'] = []
    else:
        v = nex['^ot:tag']
        if not isinstance(v, list):
            nex['^ot:tag'] = [v]
    _EMPTY_STR_TAGS = ["^ot:branchLengthDescription",
                       "^ot:branchLengthMode",
                       "^ot:branchLengthTimeUnit",
                       "^ot:outGroupEdge",
                       "^ot:specifiedRoot",
                       ]
    #_LOG.debug('nex ' + str(nex.keys()) + '\n')
    for tree_group in nex.get('treesById', {}).values():
        #_LOG.debug('tg ' + str(tree_group.keys()) + '\n')
        for tree in tree_group.get('treeById', {}).values():
            #_LOG.debug('t ' + str(tree.keys()) + '\n')
            for t in _EMPTY_STR_TAGS:
                if t not in tree:
                    tree[t] = ''
            if '^ot:tag' not in tree:
                tree['^ot:tag'] = []
            else:
                v = tree['^ot:tag']
                if not isinstance(v, list):
                    tree['^ot:tag'] = [v]


def apr_1_2014_workaround_phylografter_export_diffs(obj, out):
    _rec_resource_meta(obj, 'root')
    _coerce_boolean(obj, 'root')
    _move_ott_taxon_name_to_otu(obj)
    _move_otu_at_label_properties(obj)
    write_as_json(obj, out)

def workaround_phylografter_export_diffs(obj, out):
    workaround_phylografter_nexson(obj)
    write_as_json(obj, out)

def workaround_phylografter_nexson(obj):
    _move_otu_at_label_properties(obj)

def add_default_prop(obj, out):
    # see Jim's comment on 
    # https://groups.google.com/forum/?fromgroups&hl=en#!searchin/opentreeoflife-software/tried$20a$20commit/opentreeoflife-software/c8b_rQvUYvA/g1p-yIfmCEcJ
    _add_defaults(obj)
    write_as_json(obj, out)
