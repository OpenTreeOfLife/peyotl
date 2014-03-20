#!/usr/bin/env python
'''Functions that interact with external tools/services
'''
from peyotl.nexson_syntax import get_ot_study_info_from_nexml, \
                                 DEFAULT_NEXSON_VERSION

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

def import_nexson_from_treebase(treebase_id,
                                nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    url = _get_treebase_url(treebase_id)
    return get_ot_study_info_from_nexml(src=url,
                                        nexson_syntax_version=nexson_syntax_version)
