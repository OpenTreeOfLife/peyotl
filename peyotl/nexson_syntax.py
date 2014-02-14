#!/usr/bin/env python
'''Functions for converting between the different representations
of NexSON and the NeXML representation.
See https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/NexSON

Most notable functions are:
    write_obj_as_nexml, 
    get_ot_study_info_from_nexml, 

'''
from peyotl.utility import get_logger
from cStringIO import StringIO
import xml.dom.minidom
import codecs

#secret#hacky#cut#paste*nexsonvalidator.py#####################################
# Code for honeybadgerfish conversion of TreeBase XML to NexSON
###############################################################################
# DIRECT_HONEY_BADGERFISH is the closest to BadgerFish
DIRECT_HONEY_BADGERFISH = '1.0.0'
DEFAULT_NEXSON_VERSION = DIRECT_HONEY_BADGERFISH

BADGER_FISH_NEXSON_VERSION = '0.0.0'
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

def _add_value_to_dict_bf(d, k, v):
    '''Adds the `k`->`v` mapping to `d`, but if a previous element exists it changes
    the value of for the key to list. 

    This is used in the BadgerFish mapping convention.

    This is a simple multi-dict that is only suitable when you know that you'll never
    store a list or `None` as a value in the dict.
    '''
    prev = d.get(k)
    if prev is None:
        d[k] = v
    elif isinstance(prev, list):
        prev.append(v)
    else:
        d[k] = [prev, v]

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
    PREVENT_TRANSFORMATION, IN_FULL_OBJECT, HANDLED, CULL = range(4)
_SUBELEMENTS_OF_LITERAL_META_AS_ATT = frozenset(['content', 'datatype', 'property', 'xsi:type', 'id'])
_HANDLED_SUBELEMENTS_OF_LITERAL_META_AS_ATT = frozenset(['content', 'datatype', 'property', 'xsi:type'])
def _literal_meta_att_decision_fn(name):
    if name in _HANDLED_SUBELEMENTS_OF_LITERAL_META_AS_ATT:
        return ATT_TRANSFORM_CODE.HANDLED, None
    return ATT_TRANSFORM_CODE.IN_FULL_OBJECT, '@' + name


_SUBELEMENTS_OF_RESOURCE_META_AS_ATT = frozenset(['href', 'xsi:type', 'rel', 'id'])
_HANDLED_SUBELEMENTS_OF_RESOURCE_META_AS_ATT = frozenset(['xsi:type', 'rel'])
_OBJ_PROP_SUBELEMENTS_OF_RESOURCE_META_AS_ATT = frozenset(['href', 'id'])
def _resource_meta_att_decision_fn(name):
    if name in _HANDLED_SUBELEMENTS_OF_RESOURCE_META_AS_ATT:
        return ATT_TRANSFORM_CODE.HANDLED, None
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

def _literal_transform_meta_key_value(minidom_meta_element):
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
            assert (handling_code == ATT_TRANSFORM_CODE.HANDLED)
            
    if not att_str_val:
        att_str_val, ntl = _extract_text_and_child_element_list(minidom_meta_element)
        if len(ntl) > 0: # #TODO: the case of len(ntl) == 1, is a nested meta, and should be handled.
            _LOG.debug('Nested meta elements are not legal for LiteralMeta (offending property={p}'.format(p=att_key))
            return None
    att_key = '^' + att_key
    trans_val = _coerce_literal_val_to_primitive(dt, att_str_val)
    if trans_val is None:
        return None
    if full_obj:
        full_obj['$'] = trans_val
        _cull_redundant_about(full_obj)
        return att_key, full_obj
    return att_key, trans_val

def _resource_transform_meta_key_value(minidom_meta_element):
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
            assert (handling_code == ATT_TRANSFORM_CODE.HANDLED)
    rel = '^' + rel
    att_str_val, ntl = _extract_text_and_child_element_list(minidom_meta_element)
    if att_str_val:
        _LOG.debug('text content of ResourceMeta of rel="{r}"'.format(r=rel))
        return None
    if ntl:
        raise NotImplementedError('handling nested metas is a TODO\n')
    if not full_obj:
        _LOG.debug('ResourceMeta of rel="{r}" without condents ("href" attribute or nested meta)'.format(r=rel))
        return None
    _cull_redundant_about(full_obj)
    return rel, full_obj

def _transform_meta_key_value(minidom_meta_element):
    '''Checks if the minidom_meta_element can be represented as a
        key/value pair in a object.

    Returns (key, value) ready for JSON serialization, OR
            `None` if the element can not be treated as simple pair.
    If `None` is returned, then more literal translation of the 
        object may be required.
    '''
    xt = minidom_meta_element.getAttribute('xsi:type')
    if xt == 'nex:LiteralMeta':
        return _literal_transform_meta_key_value(minidom_meta_element)
    elif xt == 'nex:ResourceMeta':
        return _resource_transform_meta_key_value(minidom_meta_element)
    else:
        _LOG.debug('xsi:type attribute not LiteralMeta or ResourceMeta')
        return None

def _cull_redundant_about(obj):
    about_val = obj.get('@about')
    if about_val:
        id_val = obj.get('@id')
        if id_val and (('#' + id_val) == about_val):
            del obj['@about']

def _gen_hbf_el(x, nexson_syntax_version):
    '''
    Builds a dictionary from the ElementTree element x
    The function
    Uses as hacky splitting of attribute or tag names using {}
        to remove namespaces.
    returns a pair of: the tag of `x` and the honeybadgerfish
        representation of the subelements of x
    '''
    badgerfish_style_conversion = nexson_syntax_version.startswith('0.')
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
    # accumulate a list of the children names in ko, and 
    #   the a dictionary of tag to xml elements.
    # repetition of a tag means that it will map to a list of
    #   xml elements
    cd = {}
    ko = []
    ks = set()
    for child in ntl:
        k = child.nodeName
        if k == 'meta' and (not badgerfish_style_conversion):
            matk, matv = _transform_meta_key_value(child)
            _add_value_to_dict_bf(obj, matk, matv)
        else:
            if k not in ks:
                ko.append(k)
                ks.add(k)
            _add_value_to_dict_bf(cd, k, child)

    # Converts the child XML elements to dicts by recursion and
    #   adds these to the dict.
    for k in ko:
        v = cd[k]
        if not isinstance(v, list):
            v = [v]
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
    return el_name, obj

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

def _python_instance_to_nexml_meta_datatype(v):
    if isinstance(v, bool):
        return 'xsd:boolean'
    if isinstance(v, int) or isinstance(v, long):
        return 'xsd:int'
    if isinstance(v, float):
        return 'xsd:float'
    return 'xsd:string'

# based on http://www.w3.org/TR/xmlschema-2
# xsd:string is considered the default...
_OT_META_PROP_TO_DATATYPE = {
    'ot:focalClade': 'xsd:int',
    'ot:isLeaf': 'xsd:boolean',
    'ot:notIntendedForSynthesis': 'xsd:boolean',
    'ot:notUsingRootedTrees': 'xsd:boolean',
    'ot:ottid': 'xsd:int',
    'ot:studyYear' : 'xsd:int',
    }
_XSD_TYPE_TO_VALID_PYTHON_TYPES = {
    'numeric': set([float, int, long]),
    'xsd:int': set([int, long]),
    'xsd:float': set([float]),
    'xsd:boolean': set([bool]),
    'xsd:string': set([str, unicode]),
}
_XSD_TYPE_COERCION = {
    'numeric': float,
    'xsd:int': int,
    'xsd:float': float,
    'xsd:boolean': lambda x: x.lower() == 'true',
    'xsd:string': unicode,
}


def _create_sub_el(doc, parent, tag, attrib, data=None):
    el = doc.createElement(tag)
    if attrib:
        for att_key, att_value in attrib.items():
            el.setAttribute(att_key, att_value)
    if parent:
        parent.appendChild(el)
    if data:
        if data is True:
            el.appendChild(doc.createTextNode('true'))
        elif data is False:
            el.appendChild(doc.createTextNode('false'))
        else:
            el.appendChild(doc.createTextNode(unicode(data)))
    return el

def _add_nested_resource_meta(doc, parent, name, value, att_dict):
    # assuming the @href holds "value" so we don't actually use the value arg currently.
    '''tatts = {'xsi:type':  'nex:ResourceMeta',
             'rel': name}
    for k, v in att_dict.items():
        assert(k.startswith('@'))
        real_att = k[1:]
        tatts[real_att] = v
    m = _create_sub_el(doc, parent, 'meta', tatts)'''
    raise NotImplementedError('Nested Meta')
    
def _add_href_resource_meta(doc, parent, name, att_dict):
    tatts = {'xsi:type':  'nex:ResourceMeta',
             'rel': name}
    for k, v in att_dict.items():
        assert(k.startswith('@'))
        real_att = k[1:]
        tatts[real_att] = v
    return _create_sub_el(doc, parent, 'meta', tatts)

def _add_literal_meta(doc, parent, name, value, att_dict):
    # assuming the @href holds "value" so we don't actually use the value arg currently.
    tatts = {'xsi:type':  'nex:LiteralMeta',
             'datatype': _python_instance_to_nexml_meta_datatype(value),
             'property': name
             }
    for k, v in att_dict.items():
        if k in ['@content', '$']:
            continue
        assert(k.startswith('@'))
        real_att = k[1:]
        tatts[real_att] = v
    return _create_sub_el(doc, parent, 'meta', tatts, value)


def _add_meta_value_to_xml_doc(doc, parent, key, value):
    if isinstance(value, dict):
        href = value.get('@href')
        if href is None:
            content = value['$']
            if isinstance(content, dict):
                _add_nested_resource_meta(doc, parent, name=key, value=content, att_dict=value)
            else:
                _add_literal_meta(doc, parent, name=key, value=content, att_dict=value)
        else:
            _add_href_resource_meta(doc, parent, name=key, att_dict=value)
    else:
        _add_literal_meta(doc, parent, name=key, value=value, att_dict={})

def _add_meta_xml_element(doc, parent, meta_dict):
    '''
    assert key != u'meta':
            if 'datatype' not in ca:
                dsv = _OT_META_PROP_TO_DATATYPE.get(ca.get('property'))
                if dsv is None:
                    dsv = _python_instance_to_nexml_meta_datatype(cd)
                ca['datatype'] = dsv
            cel = _create_sub_el(doc, parent, u'meta', ca, cd)
    '''
    if not meta_dict:
        return
    key_list = meta_dict.keys()
    key_list.sort()
    for key in key_list:
        value = meta_dict[key]
        if isinstance(value, list):
            for el in value:
                _add_meta_value_to_xml_doc(doc, parent, key, el)
        else:
            _add_meta_value_to_xml_doc(doc, parent, key, value)

def _add_child_list_to_xml_doc_subtree(doc, parent, child_list, key, key_order, nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    if not isinstance(child_list, list):
        child_list = [child_list]
    _migrating_old_bf_form = nexson_syntax_version.startswith('0.')
    for child in child_list:
        ca, cd, cc, mc = _break_keys_by_hbf_type(child, nexson_syntax_version=nexson_syntax_version)
        if ('id' in ca) and ('about' not in ca):
            ca['about'] = '#' + ca['id']
        if _migrating_old_bf_form:
            if (key == 'tree') and ('xsi:type' not in ca):
                ca['xsi:type'] = 'nex:FloatTree'
        cel = _create_sub_el(doc, parent, key, ca, cd)
        _add_meta_xml_element(doc, cel, mc)
        _add_xml_doc_subtree(doc, cel, cc, key_order, nexson_syntax_version=nexson_syntax_version)

def _add_xml_doc_subtree(doc, parent, children_dict, key_order=None, nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    written = set()
    if key_order:
        for t in key_order:
            k, next_order_el = t
            assert(next_order_el is None or isinstance(next_order_el, tuple))
            if k in children_dict:
                child_list = children_dict[k]
                written.add(k)
                _add_child_list_to_xml_doc_subtree(doc, parent, child_list, k, next_order_el, nexson_syntax_version=nexson_syntax_version)
    ksl = children_dict.keys()
    ksl.sort()
    for k in ksl:
        child_list = children_dict[k]
        if k not in written:
            _add_child_list_to_xml_doc_subtree(doc, parent, child_list, k, None, nexson_syntax_version=nexson_syntax_version)


def _break_keys_by_hbf_type(o, nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Breaks o into a triple two dicts and text data by key type:
        attrib keys (start with '@'),
        text (value associated with the '$' or None),
        child element keys (all others)
    '''
    _migrating_old_bf_form = nexson_syntax_version.startswith('0.')
    ak = {}
    tk = None
    ck = {}
    mc = {}
    for k, v in o.items():
        if k.startswith('@'):
            if k == '@xmlns':
                ak['xmlns'] = v['$']
                for nsk, nsv in v.items():
                    if nsk != '$':
                        ak['xmlns:' + nsk] = nsv
            else:
                s = k[1:]
                ak[s] = unicode(v)
        elif k == '$':
            tk = v
        elif k.startswith('^'):
            s = k[1:]
            mc[s] = v
        elif _migrating_old_bf_form and k == 'meta':
            if not isinstance(v, list):
                v = [v]
            for val in v:
                k = val.get('@property')
                if k is None:
                    k = val.get('@rel')
                if '@property' in val:
                    del val['@property']
                if '@rel' in val:
                    del val['@rel']
                _cull_redundant_about(val)
                _add_value_to_dict_bf(mc, k, val)
        else:
            ck[k] = v
    return ak, tk, ck, mc

def get_ot_study_info_from_nexml(src, encoding=u'utf8', nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Converts an XML doc to JSON using the honeybadgerfish convention (see to_honeybadgerfish_dict)
    and then prunes elements not used by open tree of life study curartion.

    Currently:
        removes nexml/characters @TODO: should replace it with a URI for 
            where the removed character data can be found.
    '''
    o = to_honeybadgerfish_dict(src, encoding, nexson_syntax_version=nexson_syntax_version)
    try:
        if ('nexml' in o) and ('characters' in o['nexml']):
            del o['nexml']['characters']
    except:
        pass
    return o

def get_ot_study_info_from_treebase_nexml(src, encoding=u'utf8', nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Just a stub at this point. Intended to normalize treebase-specific metadata 
    into the locations where open tree of life software that expects it. 

    `src` can be a string (filepath) or a input file object.
    @TODO: need to investigate which metadata should move or be copied
    '''
    o = get_ot_study_info_from_nexml(src, encoding=encoding, nexson_syntax_version=nexson_syntax_version)
    return o


def _nex_obj_2_nexml_doc(doc, obj_dict, root_atts=None, nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    base_keys = obj_dict.keys()
    assert(len(base_keys) == 1)
    root_name = base_keys[0]
    root_obj = obj_dict[root_name]
    atts, data, children, meta_children = _break_keys_by_hbf_type(root_obj)
    atts['generator'] = 'org.opentreeoflife.api.nexsonvalidator.nexson_nexml'
    if not 'version' in atts:
        atts['version'] = '0.9'
    if root_atts:
        for k, v in root_atts.items():
            atts[k] = v
    if ('id' in atts) and ('about' not in atts):
        atts['about'] = '#' + atts['id']
    if 'nexml2json' in atts:
        del atts['nexml2json']
    r = _create_sub_el(doc, doc, root_name, atts, data)
    _add_meta_xml_element(doc, r, meta_children)
    nexml_key_order = (('meta', None),
                       ('otus', (('meta', None),
                                 ('otu', None)
                                )
                       ),
                       ('characters', (('meta', None),
                                       ('format',(('meta', None),
                                                  ('states', (('state', None),
                                                              ('uncertain_state_set', None),
                                                             )
                                                  ),
                                                  ('char', None)
                                                 ),
                                       ),
                                       ('matrix', (('meta', None),
                                                   ('row', None),
                                                  )
                                       ),
                                      ),
                       ),
                       ('trees', (('meta', None),
                                  ('tree', (('meta', None),
                                            ('node', None),
                                            ('edge', None)
                                           )
                                  )
                                 )
                       )
                      )
    _add_xml_doc_subtree(doc, r, children, nexml_key_order, nexson_syntax_version=nexson_syntax_version)


def write_obj_as_nexml(obj_dict,
                       file_obj,
                       addindent='',
                       newl='',
                       nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    root_atts = {
        "xmlns:nex": "http://www.nexml.org/2009",
        "xmlns": "http://www.nexml.org/2009",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema#",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:ot": "http://purl.org/opentree/nexson",
    }
    # extra = {
    #     "xmlns:dc": "http://purl.org/dc/elements/1.1/",
    #     "xmlns:dcterms": "http://purl.org/dc/terms/",
    #     "xmlns:prism": "http://prismstandard.org/namespaces/1.2/basic/",
    #     "xmlns:rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    #     "xmlns:rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    #     "xmlns:skos": "http://www.w3.org/2004/02/skos/core#",
    #     "xmlns:tb": "http://purl.org/phylo/treebase/2.0/terms#",
    # }
    doc = xml.dom.minidom.Document()
    _nex_obj_2_nexml_doc(doc, obj_dict, root_atts=root_atts, nexson_syntax_version=nexson_syntax_version)
    doc.writexml(file_obj, addindent=addindent, newl=newl, encoding='utf-8')

def get_nexson_version(blob):
    '''Returns the nexml2json attribute or the default code for badgerfish'''
    n = blob.get('nex:nexml') or blob.get('nexml')
    assert(n)
    return n.get('@nexml2json', BADGER_FISH_NEXSON_VERSION)

_is_badgerfish_version = lambda x: x.startswith('0.')
_is_legacy_honeybadgerfish = lambda x: x.startswith('1.0.')
_is_by_id_honedybadgerfish = lambda x: x.startswith('1.2')

def can_convert_nexson_forms(src_format, dest_format):
    return (dest_format in _CONVERTIBLE_FORMATS) and (src_format in _CONVERTIBLE_FORMATS)

def convert_nexson_format(blob, out_nexson_format, current_format=None):
    '''Take a dict form of NexSON and converts its datastructures to 
    those needed to serialize as out_nexson_format.
    If current_format is not specified, it will be inferred.
    '''
    if not current_format:
        current_format = get_nexson_version(blob)
    if current_format == out_nexson_format:
        return blob
    if _is_badgerfish_version(current_format) or _is_badgerfish_version(out_nexson_format):
        xo = StringIO()
        ci = codecs.lookup('utf8')
        s = codecs.StreamReaderWriter(xo, ci.streamreader, ci.streamwriter)
            
        write_obj_as_nexml(blob,
                           s,
                           addindent=' ',
                           newl='\n',
                           nexson_syntax_version=out_nexson_format)
        xml_content = xo.getvalue()
        xi = StringIO(xml_content)
        blob = get_ot_study_info_from_nexml(xi,
                                            nexson_syntax_version=out_nexson_format)
        return blob
    raise NotImplementedError('Conversion from {i} to {o}'.format(i=current_format, o=out_nexson_format))
################################################################################
# End of honeybadgerfish...
#end#secret#hacky#cut#paste*nexsonvalidator.py##################################
