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
                                        _is_legacy_honeybadgerfish, \
                                        BADGER_FISH_NEXSON_VERSION, \
                                        DEFAULT_NEXSON_VERSION, \
                                        DIRECT_HONEY_BADGERFISH, \
                                        NEXML_NEXSON_VERSION, \
                                        PREFERRED_HONEY_BADGERFISH

from peyotl.nexson_syntax.optimal2direct_nexson import Optimal2DirectNexson
from peyotl.nexson_syntax.direct2optimal_nexson import Direct2OptimalNexson
from peyotl.nexson_syntax.nexson2nexml import Nexson2Nexml
from peyotl.utility import get_logger
from cStringIO import StringIO
import xml.dom.minidom
import codecs
import json
import re

# TODO: in lieu of real namespace support...
_LITERAL_META_PAT = re.compile(r'.*[:]?LiteralMeta$')
_RESOURCE_META_PAT = re.compile(r'.*[:]?ResourceMeta$')

_CONVERTIBLE_FORMATS = frozenset([DEFAULT_NEXSON_VERSION,
                                  BADGER_FISH_NEXSON_VERSION])
_LOG = get_logger()

# unused cruft. Useful if we decide that some ot:... attributes should always map to arrays.
_PLURAL_META_TO_ATT_KEYS_LIST = ('@ot:candidateTreeForSynthesis', '@ot:tag', )
_PLURAL_META_TO_ATT_KEYS_SET = frozenset(_PLURAL_META_TO_ATT_KEYS_LIST)

def _debug_dump_dom(el):
    '''Debugging helper. Prints out `el` contents.'''
    s = [el.nodeName]
    att_container = el.attributes
    for i in xrange(att_container.length):
        attr = att_container.item(i)
        s.append('  @{a}="{v}"'.format(a=attr.name, v=attr.value))
    for c in el.childNodes:
        if c.nodeType == xml.dom.minidom.Node.TEXT_NODE:
            s.append('  {a} type="TEXT" data="{d}"'.format(a=c.nodeName, d=c.data))
        else:
            s.append('  {a} child'.format(a=c.nodeName))
    return '\n'.join(s)


def _extract_text_and_child_element_list(minidom_node):
    '''Returns a pair of the "child" content of minidom_node:
        the first element of the pair is a concatenation of the text content
        the second element is a list of non-text nodes.

    The string concatenation strips leading and trailing whitespace from each
    bit of text found and joins the fragments (with no separator between them).
    '''
    tl = []
    ntl = []
    for c in minidom_node.childNodes:
        if c.nodeType == xml.dom.minidom.Node.TEXT_NODE:
            tl.append(c)
        else:
            ntl.append(c)
    try:
        tl = [i.data.strip() for i in tl]
        text_content = ''.join(tl)
    except:
        text_content = ''
    return text_content, ntl


class ATT_TRANSFORM_CODE:
    PREVENT_TRANSFORMATION, IN_FULL_OBJECT, HANDLED, CULL, IN_XMLNS_OBJ = range(5)
_SUBELEMENTS_OF_LITERAL_META_AS_ATT = frozenset(['content', 'datatype', 'property', 'xsi:type', 'id'])
_HANDLED_SUBELEMENTS_OF_LITERAL_META_AS_ATT = frozenset(['content', 'datatype', 'property', 'xsi:type'])
def _literal_meta_att_decision_fn(name):
    if name in _HANDLED_SUBELEMENTS_OF_LITERAL_META_AS_ATT:
        return ATT_TRANSFORM_CODE.HANDLED, None
    if name.startswith('xmlns'):
        if name.startswith('xmlns:'):
            return ATT_TRANSFORM_CODE.IN_XMLNS_OBJ, name[6:]
        if name == 'xmlns':
            return ATT_TRANSFORM_CODE.IN_XMLNS_OBJ, '$'
    return ATT_TRANSFORM_CODE.IN_FULL_OBJECT, '@' + name


_SUBELEMENTS_OF_RESOURCE_META_AS_ATT = frozenset(['href', 'xsi:type', 'rel', 'id'])
_HANDLED_SUBELEMENTS_OF_RESOURCE_META_AS_ATT = frozenset(['xsi:type', 'rel'])
_OBJ_PROP_SUBELEMENTS_OF_RESOURCE_META_AS_ATT = frozenset(['href', 'id'])
def _resource_meta_att_decision_fn(name):
    if name in _HANDLED_SUBELEMENTS_OF_RESOURCE_META_AS_ATT:
        return ATT_TRANSFORM_CODE.HANDLED, None
    if name.startswith('xmlns'):
        if name.startswith('xmlns:'):
            return ATT_TRANSFORM_CODE.IN_XMLNS_OBJ, name[6:]
        if name == 'xmlns':
            return ATT_TRANSFORM_CODE.IN_XMLNS_OBJ, '$'
    return ATT_TRANSFORM_CODE.IN_FULL_OBJECT, '@' + name

class NexmlTypeError(Exception):
    def __init__(self, m):
        self.msg = m
    def __str__(self):
        return self.msg

def _coerce_literal_val_to_primitive(datatype, str_val):
    _TYPE_ERROR_MSG_FORMAT = 'Expected meta property to have type {t}, but found "{v}"'
    if datatype == 'xsd:string':
        return str_val
    if datatype in frozenset(['xsd:int', 'xsd:integer', 'xsd:long']):
        try:
            return int(str_val)
        except:
            raise NexmlTypeError(_TYPE_ERROR_MSG_FORMAT.format(t=datatype, v=str_val))
    elif datatype == frozenset(['xsd:float', 'xsd:double']):
        try:
            return float(str_val)
        except:
            raise NexmlTypeError(_TYPE_ERROR_MSG_FORMAT.format(t=datatype, v=str_val))
    elif datatype == 'xsd:boolean':
        if str_val.lower() in frozenset(['1', 'true']):
            return True
        elif str_val.lower() in frozenset(['0', 'false']):
            return False
        else:
            raise NexmlTypeError(_TYPE_ERROR_MSG_FORMAT.format(t=datatype, v=str_val))
    else:
        _LOG.debug('unknown xsi:type {t}'.format(t=datatype))
        return None # We'll fall through to here when we encounter types we do not recognize

def _literal_transform_meta_key_value(minidom_meta_element, nexson_syntax_version):
    att_key = None
    dt = minidom_meta_element.getAttribute('datatype') or 'xsd:string'
    att_str_val = minidom_meta_element.getAttribute('content')
    att_key = minidom_meta_element.getAttribute('property')
    full_obj = {}
    if att_key is None:
        _LOG.debug('"property" missing from literal meta')
        return None
    att_container = minidom_meta_element.attributes
    for i in xrange(att_container.length):
        attr = att_container.item(i)
        handling_code, new_name = _literal_meta_att_decision_fn(attr.name)
        if handling_code == ATT_TRANSFORM_CODE.IN_FULL_OBJECT:
            full_obj[new_name] = attr.value
        else:
            if handling_code == ATT_TRANSFORM_CODE.IN_XMLNS_OBJ:
                full_obj.setdefault('@xmlns', {})[new_name] = attr.value
            else:
                assert (handling_code == ATT_TRANSFORM_CODE.HANDLED)
            
    if not att_str_val:
        att_str_val, ntl = _extract_text_and_child_element_list(minidom_meta_element)
        att_str_val = att_str_val.strip()
        if len(ntl) > 1: # #TODO: the case of len(ntl) == 1, is a nested meta, and should be handled.
            _LOG.debug('Nested meta elements are not legal for LiteralMeta (offending property={p}'.format(p=att_key))
            return None
        if len(ntl) == 1:
            _hbf_handle_child_elements(full_obj, ntl, nexson_syntax_version)
    att_key = '^' + att_key
    trans_val = _coerce_literal_val_to_primitive(dt, att_str_val)
    if trans_val is None:
        return None
    if full_obj:
        if trans_val:
            full_obj['$'] = trans_val
        _cull_redundant_about(full_obj)
        return att_key, full_obj
    return att_key, trans_val

def _resource_transform_meta_key_value(minidom_meta_element, nexson_syntax_version):
    rel = minidom_meta_element.getAttribute('rel')
    if rel is None:
        _LOG.debug('"rel" missing from ResourceMeta')
        return None
    full_obj = {}
    att_container = minidom_meta_element.attributes
    for i in xrange(att_container.length):
        attr = att_container.item(i)
        handling_code, new_name = _resource_meta_att_decision_fn(attr.name)
        if handling_code == ATT_TRANSFORM_CODE.IN_FULL_OBJECT:
            full_obj[new_name] = attr.value
        else:
            if handling_code == ATT_TRANSFORM_CODE.IN_XMLNS_OBJ:
                full_obj.setdefault('@xmlns', {})[new_name] = attr.value
            else:
                assert (handling_code == ATT_TRANSFORM_CODE.HANDLED)
    rel = '^' + rel
    att_str_val, ntl = _extract_text_and_child_element_list(minidom_meta_element)
    if att_str_val:
        _LOG.debug('text content of ResourceMeta of rel="{r}"'.format(r=rel))
        return None
    if ntl:
        _hbf_handle_child_elements(full_obj, ntl, nexson_syntax_version)
    if not full_obj:
        _LOG.debug('ResourceMeta of rel="{r}" without condents ("href" attribute or nested meta)'.format(r=rel))
        return None
    _cull_redundant_about(full_obj)
    return rel, full_obj

def _transform_meta_key_value(minidom_meta_element, nexson_syntax_version):
    '''Checks if the minidom_meta_element can be represented as a
        key/value pair in a object.

    Returns (key, value) ready for JSON serialization, OR
            `None` if the element can not be treated as simple pair.
    If `None` is returned, then more literal translation of the 
        object may be required.
    '''
    xt = minidom_meta_element.getAttribute('xsi:type')
    if _LITERAL_META_PAT.match(xt):
        return _literal_transform_meta_key_value(minidom_meta_element, nexson_syntax_version)
    elif _RESOURCE_META_PAT.match(xt):
        return _resource_transform_meta_key_value(minidom_meta_element, nexson_syntax_version)
    else:
        _LOG.debug('xsi:type attribute "{t}" not LiteralMeta or ResourceMeta'.format(t=xt))
        return None


def _gen_hbf_el(x, nexson_syntax_version):
    '''
    Builds a dictionary from the DOM element x
    The function
    Uses as hacky splitting of attribute or tag names using {}
        to remove namespaces.
    returns a pair of: the tag of `x` and the honeybadgerfish
        representation of the subelements of x
    Indirect recursion through _hbf_handle_child_elements
    '''
    obj = {}
    # grab the tag of x
    el_name = x.nodeName
    assert el_name is not None
    # add the attributes to the dictionary
    att_container = x.attributes
    ns_obj = {}
    for i in xrange(att_container.length):
        attr = att_container.item(i)
        n = attr.name
        t = None
        if n.startswith('xmlns'):
            if n == 'xmlns':
                t = '$'
            elif n.startswith('xmlns:'):
                t = n[6:] # strip off the xmlns:
        if t is None:
            obj['@' + n] = attr.value
        else:
            ns_obj[t] = attr.value
    if ns_obj:
        obj['@xmlns'] = ns_obj

    x.normalize()
    # store the text content of the element under the key '$'
    text_content, ntl = _extract_text_and_child_element_list(x)
    if text_content:
        obj['$'] = text_content
    _hbf_handle_child_elements(obj, ntl, nexson_syntax_version)
    return el_name, obj

def _hbf_handle_child_elements(obj, ntl, nexson_syntax_version):
    '''
    Indirect recursion through _hbf_handle_child_elements
    '''
    # accumulate a list of the children names in ko, and 
    #   the a dictionary of tag to xml elements.
    # repetition of a tag means that it will map to a list of
    #   xml elements
    badgerfish_style_conversion = nexson_syntax_version.startswith('0.')
    cd = {}
    ko = []
    ks = set()
    for child in ntl:
        k = child.nodeName
        if k == 'meta' and (not badgerfish_style_conversion):
            matk, matv = _transform_meta_key_value(child, nexson_syntax_version)
            _add_value_to_dict_bf(obj, matk, matv)
        else:
            if k not in ks:
                ko.append(k)
                ks.add(k)
            _add_value_to_dict_bf(cd, k, child)

    # Converts the child XML elements to dicts by recursion and
    #   adds these to the dict.
    for k in ko:
        v = _index_list_of_values(cd, k)
        dcl = []
        ct = None
        for xc in v:
            ct, dc = _gen_hbf_el(xc, nexson_syntax_version)
            dcl.append(dc)
        # this assertion will trip is the hacky stripping of namespaces
        #   results in a name clash among the tags of the children
        assert ct not in obj
        obj[ct] = dcl

    # delete redundant about attributes that are used in XML, but not JSON (last rule of HoneyBadgerFish)
    _cull_redundant_about(obj)
    return obj

def to_honeybadgerfish_dict(src, encoding=u'utf-8', nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Takes either:
            (1) a file_object, or
            (2) (if file_object is None) a filepath and encoding
    Returns a dictionary with the keys/values encoded according to the honeybadgerfish convention
    See https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/HoneyBadgerFish

    Caveats/bugs:
        
    '''
    if isinstance(src, str):
        src = codecs.open(src, 'rU', encoding=encoding)
    content = src.read().encode('utf-8')
    doc = xml.dom.minidom.parseString(content)
    root = doc.documentElement
    key, val = _gen_hbf_el(root, nexson_syntax_version=nexson_syntax_version)
    val['@nexml2json'] = nexson_syntax_version
    return {key: val}

def _cull_redundant_about(obj):
    '''Removes the @about key from the `obj` dict if that value refers to the
    dict's '@id'
    '''
    about_val = obj.get('@about')
    if about_val:
        id_val = obj.get('@id')
        if id_val and (('#' + id_val) == about_val):
            del obj['@about']


def get_ot_study_info_from_nexml(src,
                                 encoding=u'utf8',
                                 nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Converts an XML doc to JSON using the honeybadgerfish convention (see to_honeybadgerfish_dict)
    and then prunes elements not used by open tree of life study curartion.

    Currently:
        removes nexml/characters @TODO: should replace it with a URI for 
            where the removed character data can be found.
    '''
    if nexson_syntax_version == PREFERRED_HONEY_BADGERFISH:
        nsv = DIRECT_HONEY_BADGERFISH
    else:
        nsv = nexson_syntax_version
    o = to_honeybadgerfish_dict(src, encoding, nexson_syntax_version=nsv)
    n = o.get('nexml') or o.get('nex:nexml')
    if not n:
        return o
    # ot: discard characters...
    if 'characters' in n:
            del n['characters']
    # ot: expect root=true for exactly one node in a tree.
    for trees in _get_index_list_of_values(n, 'trees'):
        for tree in _get_index_list_of_values(trees, 'tree'):
            node_list = _get_index_list_of_values(tree, 'node')
            root_node_flagged = False
            for node in node_list:
                if node.get('@root') == "true":
                    root_node_flagged = True
                    break
            if not root_node_flagged:
                node_id_map = dict((node['@id'], node) for node in node_list)
                edge_list = _get_index_list_of_values(tree, 'edge')
                target_set = set([i['@target'] for i in edge_list])
                root_id_set = set(node_id_map.keys()) - target_set
                assert(len(root_id_set) == 1)
                for ri in root_id_set:
                    node_id_map[ri]['@root'] = "true"
    if nexson_syntax_version == PREFERRED_HONEY_BADGERFISH:
        convert_nexson_format(o, PREFERRED_HONEY_BADGERFISH, current_format=nsv)
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
    return (vers.startswith('0.0') 
            or vers.startswith('1.0')
            or vers == 'nexml')
def write_obj_as_nexml(obj_dict,
                       file_obj,
                       addindent='',
                       newl='',
                       use_default_root_atts=True):
    # extra = {
    #     "xmlns:dc": "http://purl.org/dc/elements/1.1/",
    #     "xmlns:dcterms": "http://purl.org/dc/terms/",
    #     "xmlns:prism": "http://prismstandard.org/namespaces/1.2/basic/",
    #     "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    #     "xmlns:rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    #     "xmlns:skos": "http://www.w3.org/2004/02/skos/core#",
    #     "xmlns:tb": "http://purl.org/phylo/treebase/2.0/terms#",
    # }
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
    ccfg = ConversionConfig(output_format=out_nexson_format,
                            input_format=current_format, 
                            remove_old_structs=remove_old_structs,
                            pristine_if_invalid=pristine_if_invalid)
    if _is_badgerfish_version(current_format) or _is_badgerfish_version(out_nexson_format):
        xo = StringIO()
        ci = codecs.lookup('utf8')
        s = codecs.StreamReaderWriter(xo, ci.streamreader, ci.streamwriter)
        
        write_obj_as_nexml(blob,
                           s,
                           addindent=' ',
                           newl='\n',
                           use_default_root_atts=False)
        xml_content = xo.getvalue()
        xi = StringIO(xml_content)
        xiwrap = codecs.StreamReaderWriter(xi, ci.streamreader, ci.streamwriter)
        blob = get_ot_study_info_from_nexml(xiwrap,
                                            nexson_syntax_version=out_nexson_format)
        return blob
    
    converter = None
    if _is_legacy_honeybadgerfish(current_format) and (out_nexson_format == PREFERRED_HONEY_BADGERFISH):
        converter = Direct2OptimalNexson(ccfg)
    elif _is_legacy_honeybadgerfish(out_nexson_format) and (current_format == PREFERRED_HONEY_BADGERFISH):
        converter = Optimal2DirectNexson(ccfg)
    
    if converter is None:
        raise NotImplementedError('Conversion from {i} to {o}'.format(i=current_format, o=out_nexson_format))
    return converter.convert(blob)
    
def write_as_json(blob, dest, indent=0, sort_keys=True):
    if isinstance(dest, str) or isinstance(dest, unicode):
        out = codecs.open(dest, mode='w', encoding='utf-8')
    else:
        out = dest
    json.dump(blob, out, indent=indent, sort_keys=sort_keys)
    out.write('\n')

################################################################################
# End of honeybadgerfish...
#end#secret#hacky#cut#paste*nexsonvalidator.py##################################
