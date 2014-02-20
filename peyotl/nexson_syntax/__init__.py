#!/usr/bin/env python
'''Functions for converting between the different representations
of NexSON and the NeXML representation.
See https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/NexSON

Most notable functions are:
    write_obj_as_nexml,
    get_ot_study_info_from_nexml,

'''
from peyotl.nexson_syntax.helper import ConversionConfig, \
                                        NexsonConverter, \
                                        _add_value_to_dict_bf, \
                                        _get_index_list_of_values, \
                                        _index_list_of_values, \
                                        _is_badgerfish_version, \
                                        _is_by_id_honedybadgerfish, \
                                        _is_legacy_honeybadgerfish, \
                                        BADGER_FISH_NEXSON_VERSION, \
                                        DEFAULT_NEXSON_VERSION, \
                                        DIRECT_HONEY_BADGERFISH, \
                                        NEXML_NEXSON_VERSION, \
                                        PREFERRED_HONEY_BADGERFISH

from peyotl.nexson_syntax.optimal2direct_nexson import Optimal2DirectNexson

from peyotl.nexson_syntax.direct2optimal_nexson import Direct2OptimalNexson
from peyotl.nexson_syntax.badgerfish2direct_nexson import Badgerfish2DirectNexson
from peyotl.nexson_syntax.direct2badgerfish_nexson import Direct2BadgerfishNexson
from peyotl.nexson_syntax.nexson2nexml import Nexson2Nexml
from peyotl.nexson_syntax.nexml2nexson import Nexml2Nexson
from peyotl.utility import get_logger
from cStringIO import StringIO
import xml.dom.minidom
import codecs
import json

_CONVERTIBLE_FORMATS = frozenset([DEFAULT_NEXSON_VERSION,
                                  BADGER_FISH_NEXSON_VERSION])
_LOG = get_logger()

def get_ot_study_info_from_nexml(src,
                                 encoding=u'utf8',
                                 nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Converts an XML doc to JSON using the honeybadgerfish convention (see to_honeybadgerfish_dict)
    and then prunes elements not used by open tree of life study curartion.

    src can be either:
            (1) a file_object, or
            (2) (if file_object is None) a filepath and encoding
    Returns a dictionary with the keys/values encoded according to the honeybadgerfish convention
    See https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/HoneyBadgerFish

    Currently:
        removes nexml/characters @TODO: should replace it with a URI for
            where the removed character data can be found.
    '''
    if nexson_syntax_version == PREFERRED_HONEY_BADGERFISH:
        nsv = DIRECT_HONEY_BADGERFISH
    else:
        nsv = nexson_syntax_version
    if isinstance(src, str):
        src = codecs.open(src, 'rU', encoding=encoding)
    content = src.read().encode('utf-8')
    doc = xml.dom.minidom.parseString(content)
    doc_root = doc.documentElement

    ccfg = ConversionConfig(output_format=nsv, input_format=NEXML_NEXSON_VERSION)
    converter = Nexml2Nexson(ccfg)
    o = converter.convert(doc_root)
    if nexson_syntax_version == PREFERRED_HONEY_BADGERFISH:
        return convert_nexson_format(o, PREFERRED_HONEY_BADGERFISH, current_format=nsv)
    return o

def get_ot_study_info_from_treebase_nexml(src, encoding=u'utf8', nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Just a stub at this point. Intended to normalize treebase-specific metadata
    into the locations where open tree of life software that expects it.

    `src` can be a string (filepath) or a input file object.
    @TODO: need to investigate which metadata should move or be copied
    '''
    o = get_ot_study_info_from_nexml(src, encoding=encoding, nexson_syntax_version=nexson_syntax_version)
    return o

def _nexson_directly_translatable_to_nexml(vers):
    'TEMP: until we refactor nexml writing code to be more general...'
    return (_is_badgerfish_version(vers)
            or _is_legacy_honeybadgerfish(vers)
            or vers == 'nexml')

def write_obj_as_nexml(obj_dict,
                       file_obj,
                       addindent='',
                       newl='',
                       use_default_root_atts=True):
    nsv = detect_nexson_version(obj_dict)
    if not _nexson_directly_translatable_to_nexml(nsv):
        convert_nexson_format(obj_dict, DIRECT_HONEY_BADGERFISH)
        nsv = DIRECT_HONEY_BADGERFISH
    ccfg = ConversionConfig(NEXML_NEXSON_VERSION,
                            input_format=nsv,
                            use_default_root_atts=use_default_root_atts)
    converter = Nexson2Nexml(ccfg)
    doc = converter.convert(obj_dict)
    doc.writexml(file_obj, addindent=addindent, newl=newl, encoding='utf-8')

def detect_nexson_version(blob):
    '''Returns the nexml2json attribute or the default code for badgerfish'''
    n = blob.get('nex:nexml') or blob.get('nexml')
    assert(n)
    return n.get('@nexml2json', BADGER_FISH_NEXSON_VERSION)

def can_convert_nexson_forms(src_format, dest_format):
    return (dest_format in _CONVERTIBLE_FORMATS) and (src_format in _CONVERTIBLE_FORMATS)

def convert_nexson_format(blob,
                          out_nexson_format,
                          current_format=None,
                          remove_old_structs=True,
                          pristine_if_invalid=False):
    '''Take a dict form of NexSON and converts its datastructures to
    those needed to serialize as out_nexson_format.
    If current_format is not specified, it will be inferred.
    If `remove_old_structs` is False and different honeybadgerfish varieties
        are selected, the `blob` will be "fat" containing both types
        of lookup structures.
    If pristine_if_invalid is False, then the object may be corrupted if it
        is an invalid nexson struct. Setting this to False can result in
        faster translation, but if an exception is raised the object may
        be polluted with partially constructed fields for the out_nexson_format.
    '''
    if not current_format:
        current_format = detect_nexson_version(blob)

    if current_format == out_nexson_format:
        return blob
    through_nexml = _is_badgerfish_version(out_nexson_format)
    if (_is_by_id_honedybadgerfish(out_nexson_format) and _is_badgerfish_version(current_format)
        or _is_by_id_honedybadgerfish(current_format) and _is_badgerfish_version(out_nexson_format)):
        # go from 0.0 -> 1.0 then the 1.0->1.2 should succeed without nexml...
        blob = convert_nexson_format(blob, 
                                     DIRECT_HONEY_BADGERFISH,
                                     current_format=current_format,
                                     remove_old_structs=remove_old_structs,
                                     pristine_if_invalid=pristine_if_invalid)
        current_format = DIRECT_HONEY_BADGERFISH
    ccdict = {'output_format':out_nexson_format,
              'input_format':current_format,
              'remove_old_structs': remove_old_structs,
              'pristine_if_invalid': pristine_if_invalid}
    ccfg = ConversionConfig(ccdict)
    if _is_badgerfish_version(current_format):
        converter = Badgerfish2DirectNexson(ccfg)
    elif _is_badgerfish_version(out_nexson_format):
        assert(_is_legacy_honeybadgerfish(current_format))
        converter = Direct2BadgerfishNexson(ccfg)
    elif _is_legacy_honeybadgerfish(current_format) and (out_nexson_format == PREFERRED_HONEY_BADGERFISH):
        converter = Direct2OptimalNexson(ccfg)
    elif _is_legacy_honeybadgerfish(out_nexson_format) and (current_format == PREFERRED_HONEY_BADGERFISH):
        converter = Optimal2DirectNexson(ccfg)
    else:
        raise NotImplementedError('Conversion from {i} to {o}'.format(i=current_format, o=out_nexson_format))
    return converter.convert(blob)

def write_as_json(blob, dest, indent=0, sort_keys=True):
    if isinstance(dest, str) or isinstance(dest, unicode):
        out = codecs.open(dest, mode='w', encoding='utf-8')
    else:
        out = dest
    json.dump(blob, out, indent=indent, sort_keys=sort_keys)
    out.write('\n')

def _recursive_sort_meta(blob, k):
    if isinstance(blob, list):
        for i in blob:
            _recursive_sort_meta(i, k)
    else:
        for inner_k, v in blob.items():
            if inner_k == 'meta' and isinstance(v, list):
                sl = []
                incd = {}
                for el in v:
                    sk = el.get('@property') or el.get('@rel') or ''
                    count = incd.setdefault(sk, 0)
                    incd[sk] = 1 + count
                    sl.append((sk, count, el))
                sl.sort()
                del v[:] # clear out the value in place
                v.extend([i[2] for i in sl]) # replace it with the item from the sorted list
            if isinstance(v, list) or isinstance(v, dict):
                _recursive_sort_meta(v, inner_k)

def sort_meta_elements(blob):
    '''For v0.0 (which has meta values in a list), this
    function recursively walks through the object 
    and sorts each meta by @property or @rel values.
    '''
    v = detect_nexson_version(blob)
    if _is_badgerfish_version(v):
        _recursive_sort_meta(blob, '')
    return blob

def _inplace_sort_by_id(unsorted_list):
    '''Takes a list of dicts each of which has an '@id' key, 
    sorts the elements in the list by the value of the @id key.
    Assumes that @id is unique or the dicts have a meaningul < operator
    '''
    if not isinstance(unsorted_list, list):
        return
    sorted_list = [(i.get('@id'), i) for i in unsorted_list]
    sorted_list.sort()
    del unsorted_list[:]
    unsorted_list.extend([i[1] for i in sorted_list])

def sort_arbitrarily_ordered_nexson(blob):
    '''Primarily used for testing (getting nice diffs). Calls
    sort_meta_elements and then sorts otu, node and edge list by id
    '''
    sort_meta_elements(blob)
    # otu, node and edge elements have no necessary orger in v0.0 or v1.0
    v = detect_nexson_version(blob)
    if _is_by_id_honedybadgerfish(v):
        return blob
    nex = blob.get('nex:nexml') or blob['nexml']
    for ob in _get_index_list_of_values(nex, 'otus'):
        _inplace_sort_by_id(ob.get('otu', []))
    for tb in _get_index_list_of_values(nex, 'trees'):
        for tree in _get_index_list_of_values(tb, 'tree'):
            _inplace_sort_by_id(tree.get('node', []))
            _inplace_sort_by_id(tree.get('edge', []))
    return blob