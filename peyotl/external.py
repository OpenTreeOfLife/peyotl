#!/usr/bin/env python
'''Functions that interact with external tools/services
'''
from peyotl.nexson_syntax import get_ot_study_info_from_nexml, \
                                 DEFAULT_NEXSON_VERSION, \
                                 BY_ID_HONEY_BADGERFISH, \
                                 convert_nexson_format, \
                                 sort_arbitrarily_ordered_nexson
from peyotl.nexson_syntax.helper import _simplify_all_meta_by_id_del

def _get_treebase_url(treebase_id):
    # Use TreeBASE API to fetch NeXML, then pass it as a string
    # to _import_nexson_from_nexml()

    # EXAMPLE: Here's Phylografter's fetch URL for study 15515 as 'nexml' (versus 'nexus'):
    #   http://purl.org/phylo/treebase/phylows/study/TB2:S15515?format=nexml
    # ... which redirects to:
    #   http://treebase.org/treebase-web/phylows/study/TB2:S15515?format=nexml
    # ... which redirects to:
    #   http://treebase.org/treebase-web/search/downloadAStudy.html?id=15515&format=nexml
    #
    # Since our download follows redirects, let's respect the PhyloWS API on treebase.org
    url_format = 'http://treebase.org/treebase-web/phylows/study/TB2:S{t:d}?format=nexml'
    return url_format.format(t=treebase_id)


def get_ot_study_info_from_treebase_nexml(src=None,
                                          nexml_content=None,
                                          encoding=u'utf8',
                                          nexson_syntax_version=DEFAULT_NEXSON_VERSION,
                                          merge_blocks=True,
                                          sort_arbitrary=False):
    '''Normalize treebase-specific metadata into the locations where
    open tree of life software that expects it.

    See get_ot_study_info_from_nexml for the explanation of the src,
    nexml_content, encoding, and nexson_syntax_version arguments
    If merge_blocks is True then peyotl.manip.merge_otus_and_trees

    Actions to "normalize" TreeBase objects to ot Nexson
        1. the meta id for any meta item that has only a value and an id
        2. throw away rdfs:isDefinedBy
        3. otu @label -> otu ^ot:originalLabel
        4. ^tb:indentifier.taxon, ^tb:indentifier.taxonVariant and some skos:closeMatch
            fields to ^ot:taxonLink
        5. remove "@xml:base"
        6. coerce edge lengths to native types
    '''
    raw = get_ot_study_info_from_nexml(src=src,
                                     nexml_content=nexml_content,
                                     encoding=encoding,
                                     nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
    nexml = raw['nexml']
    SKOS_ALT_LABEL = '^skos:altLabel'
    SKOS_CLOSE_MATCH = '^skos:closeMatch'
    strippable_pre = {
        'http://www.ubio.org/authority/metadata.php?lsid=urn:lsid:ubio.org:namebank:': '@ubio',
        'http://purl.uniprot.org/taxonomy/': '@uniprot',
    }
    moveable2taxon_link = {"^tb:identifier.taxon": '@tb:identifier.taxon',
                           "^tb:identifier.taxonVariant": '@tb:identifier.taxonVariant',
                           }
    to_del = ['^rdfs:isDefinedBy', '@xml:base']
    for tag in to_del:
        if tag in nexml:
            del nexml[tag]
    _simplify_all_meta_by_id_del(nexml)
    _otu2label = {}
    prefix_map = {}
    # compose dataDeposit
    nexid = nexml['@id']
    tb_url = 'http://purl.org/phylo/treebase/phylows/study/TB2:' + nexid
    nexml['^ot:dataDeposit'] = {'@href': tb_url}
    # compose dataDeposit
    bd = nexml.get("^dcterms:bibliographicCitation")
    if bd:
        nexml['^ot:studyPublicationReference'] = bd
    doi = nexml.get('^prism:doi')
    if doi:
        nexml['^ot:studyPublication'] = {'@href': doi}
    year = nexml.get('^prism:publicationDate')
    if year:
        try:
            nexml['^ot:studyYear'] = int(year)
        except:
            pass
    #
    for otus in nexml['otusById'].values():
        for tag in to_del:
            if tag in otus:
                del otus[tag]
        _simplify_all_meta_by_id_del(otus)
        for oid, otu in otus['otuById'].items():
            for tag in to_del:
                if tag in otu:
                    del otu[tag]
            _simplify_all_meta_by_id_del(otu)
            label = otu['@label']
            _otu2label[oid] = label
            otu['^ot:originalLabel'] = label
            del otu['@label']
            al = otu.get(SKOS_ALT_LABEL)
            if al is not None:
                if isinstance(al, dict):
                    otu[SKOS_ALT_LABEL]['source'] = 'TreeBase'
                else:
                    otu[SKOS_ALT_LABEL] = {'$': al, 'source': 'TreeBase'}
            tl = {}
            scm = otu.get(SKOS_CLOSE_MATCH)
            #_LOG.debug('scm = ' + str(scm))
            if scm:
                if isinstance(scm, dict):
                    h = scm.get('@href')
                    if h:
                        try:
                            for p, t in strippable_pre.items():
                                if h.startswith(p):
                                    ident = h[len(p):]
                                    tl[t] = ident
                                    del otu[SKOS_CLOSE_MATCH]
                                    prefix_map[t] = p
                        except:
                            pass
                else:
                    nm = []
                    try:
                        for el in scm:
                            h = el.get('@href')
                            if h:
                                found = False
                                for p, t in strippable_pre.items():
                                    if h.startswith(p):
                                        ident = h[len(p):]
                                        tl[t] = ident
                                        found = True
                                        prefix_map[t] = p
                                        break
                                if not found:
                                    nm.append(el)
                    except:
                        pass
                    if len(nm) < len(scm):
                        if len(nm) > 1:
                            otu[SKOS_CLOSE_MATCH] = nm
                        elif len(nm) == 1:
                            otu[SKOS_CLOSE_MATCH] = nm[0]
                        else:
                            del otu[SKOS_CLOSE_MATCH]
            #_LOG.debug('tl =' + str(tl))
            for k, t in moveable2taxon_link.items():
                al = otu.get(k)
                if al:
                    tl[t] = al
                    del otu[k]
            if tl:
                otu['^ot:taxonLink'] = tl
    for trees in nexml['treesById'].values():
        for tag in to_del:
            if tag in trees:
                del trees[tag]
        _simplify_all_meta_by_id_del(trees)
        for tree in trees['treeById'].values():
            for tag in to_del:
                if tag in tree:
                    del tree[tag]
            _simplify_all_meta_by_id_del(tree)
            tt = tree.get('@xsi:type', 'nex:FloatTree')
            if tt.lower() == 'nex:inttree':
                e_len_coerce = int
            else:
                e_len_coerce = float
            for edge_d in tree['edgeBySourceId'].values():
                for edge in edge_d.values():
                    try:
                        x = e_len_coerce(edge['@length'])
                        edge['@length'] = x
                    except:
                        pass
            for node in tree['nodeById'].values():
                nl = node.get('@label')
                if nl:
                    no = node['@otu']
                    if no and _otu2label[no] == nl:
                        del node['@label']

    if prefix_map:
        nexml['^ot:taxonLinkPrefixes'] = prefix_map
    if merge_blocks:
        from peyotl.manip import merge_otus_and_trees
        merge_otus_and_trees(raw)
    if nexson_syntax_version != BY_ID_HONEY_BADGERFISH:
        convert_nexson_format(raw,
                              nexson_syntax_version,
                              current_format=BY_ID_HONEY_BADGERFISH,
                              sort_arbitrary=sort_arbitrary)
    elif sort_arbitrary:
        sort_arbitrarily_ordered_nexson(raw)
    return raw


def import_nexson_from_treebase(treebase_id,
                                nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    url = _get_treebase_url(treebase_id)
    return get_ot_study_info_from_treebase_nexml(src=url,
                                                 nexson_syntax_version=nexson_syntax_version)
