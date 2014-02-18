#!/usr/bin/env python
'Nexson2Nexml class'
from peyotl.nexson_syntax.helper import ConversionConfig, \
                                        NexsonConverter, \
                                        _add_value_to_dict_bf, \
                                        _index_list_of_values, \
                                        _is_badgerfish_version, \
                                        DIRECT_HONEY_BADGERFISH
from peyotl.utility import get_logger
import xml.dom.minidom
_LOG = get_logger(__name__)


def _create_sub_el(doc, parent, tag, attrib, data=None):
    '''Creates and xml element for the `doc` with the given `parent`
    and `tag` as the tagName. 
    `attrib` should be a dictionary of string keys to primitives or dicts
        if the value is a dict, then the keys of the dict are joined with 
        the `attrib` key using a colon. This deals with the badgerfish 
        convention of nesting xmlns: attributes in a @xmnls object
    If `data` is not None, then it will be written as data. If it is a boolean, 
        the xml true false will be writtten. Otherwise it will be 
        converted to python unicode string, stripped and written.
    Returns the element created
    '''
    el = doc.createElement(tag)
    if attrib:
        if ('id' in attrib) and ('about' not in attrib):
            about_val = '#' + attrib['id']
            el.setAttribute('about', about_val)
        for att_key, att_value in attrib.items():
            if isinstance(att_value, dict):
                for inner_key, inner_val in att_value.items():
                    rk = ':'.join([att_key, inner_key])
                    el.setAttribute(rk, inner_val)
            else:
                el.setAttribute(att_key, att_value)
    if parent:
        parent.appendChild(el)
    if data:
        if data is True:
            el.appendChild(doc.createTextNode('true'))
        elif data is False:
            el.appendChild(doc.createTextNode('false'))
        else:
            u = unicode(data).strip()
            if u:
                el.appendChild(doc.createTextNode(u))
    return el

def _contains_hbf_meta_keys(d):
    for k in d.keys():
        if k.startswith('^'):
            return True
    return False

def _python_instance_to_nexml_meta_datatype(v):
    '''Returns 'xsd:string' or a more specific type for a <meta datatype="XYZ"...
    syntax using introspection.
    '''
    if isinstance(v, bool):
        return 'xsd:boolean'
    if isinstance(v, int) or isinstance(v, long):
        return 'xsd:int'
    if isinstance(v, float):
        return 'xsd:float'
    return 'xsd:string'


def _convert_hbf_meta_val_for_xml(key, val):
    '''Convert to a BadgerFish-style dict for addition to the xml tree'''
    if isinstance(val, list):
        return [_convert_hbf_meta_val_for_xml(key, i) for i in val]
    is_literal = True
    content = None
    if isinstance(val, dict):
        ret = val
        if '@href' in val:
            is_literal = False
        else:
            content = val.get('$')
            if isinstance(content, dict) and _contains_hbf_meta_keys(val):
                is_literal = False
    else:
        ret = {}
        content = val
    if is_literal:
        ret.setdefault('@xsi:type', 'nex:LiteralMeta')
        ret.setdefault('@property', key)
        if content is not None:
             ret.setdefault('@datatype', _python_instance_to_nexml_meta_datatype(content))
        if ret is not val:
            ret['$'] = content
    else:
        ret.setdefault('@xsi:type', 'nex:ResourceMeta')
        ret.setdefault('@rel', key)
    return ret

def _convert_bf_meta_val_for_xml(blob):
    if not isinstance(blob, list):
        blob = [blob]
    first_blob = blob[0]
    try:
        try:
            if first_blob.get("@xsi:type") == "nex:LiteralMeta":
                return first_blob["@property"], blob
        except:
            pass
        return first_blob["@rel"], blob
    except:
        return "", blob
class Nexson2Nexml(NexsonConverter):
    '''Conversion of the optimized (v 1.2) version of NexSON to 
    the more direct (v 1.0) port of NeXML
    This is a dict-to-minidom-doc conversion. No serialization is included.
    '''
    def __init__(self, conv_cfg):
        NexsonConverter.__init__(self, conv_cfg)
        assert(hasattr(self, 'input_format'))
        self.use_default_root_atts = conv_cfg.get('use_default_root_atts', True)
        self._migrating_from_bf = _is_badgerfish_version(self.input_format)
        # TreeBase and phylografter trees often lack the tree xsi:type
        self._adding_tree_xsi_type = True

    def convert(self, blob):
        doc = xml.dom.minidom.Document()
        self._top_level_build_xml(doc, blob)
        return doc

    def _partition_keys_for_xml(self, o):
        '''Breaks o into four content type by key syntax:
            attrib keys (start with '@'),
            text (value associated with the '$' or None),
            child element keys (all others)
            meta element
        '''
        ak = {}
        tk = None
        ck = {}
        mc = {}
        for k, v in o.items():
            if k.startswith('@'):
                if k == '@xmlns':
                    if '$' in v:
                        ak['xmlns'] = v['$']
                    for nsk, nsv in v.items():
                        if nsk != '$':
                            ak['xmlns:' + nsk] = nsv
                else:
                    s = k[1:]
                    ak[s] = unicode(v)
            elif k == '$':
                tk = v
            elif k.startswith('^') and (not self._migrating_from_bf):
                s = k[1:]
                val = _convert_hbf_meta_val_for_xml(s, v)
                _add_value_to_dict_bf(mc, s, val)
            elif (k == u'meta') and self._migrating_from_bf:
                s, val = _convert_bf_meta_val_for_xml(v)
                _add_value_to_dict_bf(mc, s, val)
            else:
                ck[k] = v
        return ak, tk, ck, mc

    def _top_level_build_xml(self, doc, obj_dict):
        if self.use_default_root_atts:
            root_atts = {
                "xmlns:nex": "http://www.nexml.org/2009",
                "xmlns": "http://www.nexml.org/2009",
                "xmlns:xsd": "http://www.w3.org/2001/XMLSchema#",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xmlns:ot": "http://purl.org/opentree/nexson",
            }
        else: 
            root_atts = {}
        base_keys = obj_dict.keys()
        assert(len(base_keys) == 1)
        root_name = base_keys[0]
        root_obj = obj_dict[root_name]
        atts, data, children, meta_children = self._partition_keys_for_xml(root_obj)
        if 'generator' not in atts:
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
        self._add_meta_dict_to_xml(doc, r, meta_children)
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
        self._add_dict_of_subtree_to_xml_doc(doc, r, children, nexml_key_order)

    def _add_subtree_list_to_xml_doc(self, doc, par, ch_list, key, key_order):
        for child in ch_list:
            self._add_subtree_to_xml_doc(doc, par, child, key, key_order)


    def _add_dict_of_subtree_to_xml_doc(self,
                                        doc,
                                        parent,
                                        children_dict,
                                        key_order=None):
        written = set()
        if key_order:
            for t in key_order:
                k, nko = t
                assert(nko is None or isinstance(nko, tuple))
                if k in children_dict:
                    chl = _index_list_of_values(children_dict, k)
                    written.add(k)
                    self._add_subtree_list_to_xml_doc(doc, parent, chl, k, nko)
        ksl = children_dict.keys()
        ksl.sort()
        for k in ksl:
            chl = _index_list_of_values(children_dict, k)
            if k not in written:
                self._add_subtree_list_to_xml_doc(doc, parent, chl, k, None)


    def _add_subtree_to_xml_doc(self,
                                doc,
                                parent,
                                subtree,
                                key,
                                key_order,
                                extra_atts=None,
                                del_atts=None):
        ca, cd, cc, mc = self._partition_keys_for_xml(subtree)
        if extra_atts is not None:
            ca.update(extra_atts)
        if del_atts is not None:
            for da in del_atts:
                if da in ca:
                    del ca[da]
        if self._adding_tree_xsi_type:
            if (key == 'tree') and (parent.tagName == 'trees') and ('xsi:type' not in ca):
                ca['xsi:type'] = 'nex:FloatTree'
        cel = _create_sub_el(doc, parent, key, ca, cd)
        self._add_meta_dict_to_xml(doc, cel, mc)
        self._add_dict_of_subtree_to_xml_doc(doc, cel, cc, key_order)
        return cel

    def _add_meta_dict_to_xml(self, doc, parent, meta_dict):
        '''
        Values in the meta element dict are converted to a BadgerFish-style
            encoding (see _convert_hbf_meta_val_for_xml), so regardless of input_format,
            we treat them as if they were BadgerFish.
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
            el_list = _index_list_of_values(meta_dict, key)
            for el in el_list:
                self._add_meta_value_to_xml_doc(doc, parent, el)

    def _add_meta_value_to_xml_doc(self, doc, parent, obj):
        '''Values in the meta element dict are converted to a BadgerFish-style
            encoding (see _convert_hbf_meta_val_for_xml), so regardless of input_format,
            we treat them as if they were BadgerFish.
        '''
        return self._add_subtree_to_xml_doc(doc,
                                            parent,
                                            subtree=obj,
                                            key='meta',
                                            key_order=None)

