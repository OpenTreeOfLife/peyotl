#!/usr/bin/env python
'Nexml2Nexson class'
from peyotl.nexson_syntax.helper import ConversionConfig, \
                                        NexsonConverter, \
                                        _add_value_to_dict_bf, \
                                        _get_index_list_of_values, \
                                        _index_list_of_values, \
                                        _is_badgerfish_version
from peyotl.utility import get_logger
import xml.dom.minidom
import re
_LOG = get_logger(__name__)

# TODO: in lieu of real namespace support...
_LITERAL_META_PAT = re.compile(r'.*[:]?LiteralMeta$')
_RESOURCE_META_PAT = re.compile(r'.*[:]?ResourceMeta$')

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

def _cull_redundant_about(obj):
    '''Removes the @about key from the `obj` dict if that value refers to the
    dict's '@id'
    '''
    about_val = obj.get('@about')
    if about_val:
        id_val = obj.get('@id')
        if id_val and (('#' + id_val) == about_val):
            del obj['@about']

class Nexml2Nexson(NexsonConverter):
    '''Conversion of the optimized (v 1.2) version of NexSON to 
    the more direct (v 1.0) port of NeXML
    This is a dict-to-minidom-doc conversion. No serialization is included.
    '''
    def __init__(self, conv_cfg):
        NexsonConverter.__init__(self, conv_cfg)
        self._badgerfish_style_conversion = _is_badgerfish_version(conv_cfg.output_format)

    def convert(self, doc_root):
        key, val = self._gen_hbf_el(doc_root)
        val['@nexml2json'] = self.output_format
        o = {key: val}
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
        return o

    def _gen_hbf_el(self, x):
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
        text_content, ntl = self._extract_text_and_child_element_list(x)
        if text_content:
            obj['$'] = text_content
        self._hbf_handle_child_elements(obj, ntl)
        return el_name, obj

    def _extract_text_and_child_element_list(self, minidom_node):
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

    def _hbf_handle_child_elements(self, obj, ntl):
        '''
        Indirect recursion through _gen_hbf_el
        '''
        # accumulate a list of the children names in ko, and 
        #   the a dictionary of tag to xml elements.
        # repetition of a tag means that it will map to a list of
        #   xml elements
        cd = {}
        ko = []
        ks = set()
        for child in ntl:
            k = child.nodeName
            if k == 'meta' and (not self._badgerfish_style_conversion):
                matk, matv = self._transform_meta_key_value(child)
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
                ct, dc = self._gen_hbf_el(xc)
                dcl.append(dc)
            # this assertion will trip is the hacky stripping of namespaces
            #   results in a name clash among the tags of the children
            assert ct not in obj
            obj[ct] = dcl

        # delete redundant about attributes that are used in XML, but not JSON (last rule of HoneyBadgerFish)
        _cull_redundant_about(obj)
        return obj

    def _literal_transform_meta_key_value(self, minidom_meta_element):
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
            att_str_val, ntl = self._extract_text_and_child_element_list(minidom_meta_element)
            att_str_val = att_str_val.strip()
            if len(ntl) > 1: # #TODO: the case of len(ntl) == 1, is a nested meta, and should be handled.
                _LOG.debug('Nested meta elements are not legal for LiteralMeta (offending property={p}'.format(p=att_key))
                return None
            if len(ntl) == 1:
                self._hbf_handle_child_elements(full_obj, ntl)
        att_key = '^' + att_key
        trans_val = self._coerce_literal_val_to_primitive(dt, att_str_val)
        if trans_val is None:
            return None
        if full_obj:
            if trans_val:
                full_obj['$'] = trans_val
            _cull_redundant_about(full_obj)
            return att_key, full_obj
        return att_key, trans_val

    def _resource_transform_meta_key_value(self, minidom_meta_element):
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
        att_str_val, ntl = self._extract_text_and_child_element_list(minidom_meta_element)
        if att_str_val:
            _LOG.debug('text content of ResourceMeta of rel="{r}"'.format(r=rel))
            return None
        if ntl:
            self._hbf_handle_child_elements(full_obj, ntl)
        if not full_obj:
            _LOG.debug('ResourceMeta of rel="{r}" without condents ("href" attribute or nested meta)'.format(r=rel))
            return None
        _cull_redundant_about(full_obj)
        return rel, full_obj

    def _transform_meta_key_value(self, minidom_meta_element):
        '''Checks if the minidom_meta_element can be represented as a
            key/value pair in a object.

        Returns (key, value) ready for JSON serialization, OR
                `None` if the element can not be treated as simple pair.
        If `None` is returned, then more literal translation of the 
            object may be required.
        '''
        xt = minidom_meta_element.getAttribute('xsi:type')
        if _LITERAL_META_PAT.match(xt):
            return self._literal_transform_meta_key_value(minidom_meta_element)
        elif _RESOURCE_META_PAT.match(xt):
            return self._resource_transform_meta_key_value(minidom_meta_element)
        else:
            _LOG.debug('xsi:type attribute "{t}" not LiteralMeta or ResourceMeta'.format(t=xt))
            return None

    def _coerce_literal_val_to_primitive(self, datatype, str_val):
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
