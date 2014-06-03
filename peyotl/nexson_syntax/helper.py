#!/usr/bin/env python
'''Basic functions and classes which are used by nexson_syntax subpackage,
but do not depend on other parts of peyotl.nexson_syntax
'''
import re
from peyotl.utility import get_logger
_LOG = get_logger(__name__)
# DIRECT_HONEY_BADGERFISH is the closest to BadgerFish
DIRECT_HONEY_BADGERFISH = '1.0.0'
BY_ID_HONEY_BADGERFISH = '1.2.1'
DEFAULT_NEXSON_VERSION = BY_ID_HONEY_BADGERFISH

BADGER_FISH_NEXSON_VERSION = '0.0.0'
NEXML_NEXSON_VERSION = 'nexml'

SUPPORTED_NEXSON_VERSIONS = frozenset([BADGER_FISH_NEXSON_VERSION,
                                       DIRECT_HONEY_BADGERFISH,
                                       BY_ID_HONEY_BADGERFISH])
SUPPORTED_NEXSON_VERSIONS_AND_ALIASES = frozenset([BADGER_FISH_NEXSON_VERSION,
                                                   DIRECT_HONEY_BADGERFISH,
                                                   BY_ID_HONEY_BADGERFISH,
                                                   '0',
                                                   '0.0',
                                                   '1.0',
                                                   '1.2'])
# TODO: in lieu of real namespace support...
_LITERAL_META_PAT = re.compile(r'.*[:]?LiteralMeta$')
_RESOURCE_META_PAT = re.compile(r'.*[:]?ResourceMeta$')

def detect_nexson_version(blob):
    '''Returns the nexml2json attribute or the default code for badgerfish'''
    n = get_nexml_el(blob)
    assert isinstance(n, dict)
    return n.get('@nexml2json', BADGER_FISH_NEXSON_VERSION)

def get_nexml_el(blob):
    v = blob.get('nexml')
    if v is not None:
        return v
    return blob['nex:nexml']

class NexmlTypeError(Exception):
    def __init__(self, m):
        self.msg = m
    def __str__(self):
        return self.msg

class ConversionConfig(object):
    def __init__(self, output_format, **kwargs):
        self._keys = ['output_format']
        self.output_format = output_format
        for k, v in kwargs.items():
            self.__dict__[k] = v
            self._keys.append(k)
    def items(self):
        for k in self._keys:
            yield (k, getattr(self, k))
    def keys(self):
        return list(self._keys)
    def get(self, k, default):
        return getattr(self, k, default)

class NexsonConverter(object):
    def __init__(self, conv_cfg):
        self._conv_cfg = conv_cfg
        for k, v in conv_cfg.items():
            self.__dict__[k] = v
        self.remove_old_structs = conv_cfg.get('remove_old_structs', True)
        self.pristine_if_invalid = conv_cfg.get('pristine_if_invalid', False)

def _index_list_of_values(d, k):
    '''Returns d[k] or [d[k]] if the value is not a list'''
    v = d[k]
    if isinstance(v, list):
        return v
    return [v]

def _get_index_list_of_values(d, k, def_value=None):
    '''Like _index_list_of_values, but uses get to access and
    returns an empty list if the key is absent.
    Returns d[k] or [d[k]] if the value is not a list'''
    v = d.get(k, def_value)
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]

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
        if isinstance(v, list):
            prev.extend(v)
        else:
            prev.append(v)
    else:
        if isinstance(v, list):
            x = [prev]
            x.extend(v)
            d[k] = x
        else:
            d[k] = [prev, v]
def _add_uniq_value_to_dict_bf(d, k, v):
    '''Like _add_value_to_dict_bf but will not add v if another
    element in under key `k` has the same value.
    '''
    prev = d.get(k)
    if prev is None:
        d[k] = v
    elif isinstance(prev, list):
        if not isinstance(v, list):
            v = [v]
        for sel in v:
            found = False
            for el in prev:
                if el == sel:
                    found = True
                    break
            if not found:
                prev.append(sel)
    else:
        if isinstance(v, list):
            prev = [prev]
            for sel in v:
                found = False
                for el in prev:
                    if el == sel:
                        found = True
                        break
                if not found:
                    prev.append(sel)
            if len(prev) > 1:
                d[k] = prev
        elif prev != v:
            d[k] = [prev, v]
_is_badgerfish_version = lambda x: x.startswith('0.')
_is_direct_hbf = lambda x: x.startswith('1.0.')
_is_by_id_hbf = lambda x: x.startswith('1.2')
_is_supported_nexson_vers = lambda x: x in SUPPORTED_NEXSON_VERSIONS_AND_ALIASES

def _debug_dump_dom(el):
    '''Debugging helper. Prints out `el` contents.'''
    import xml.dom.minidom
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

def _cull_redundant_about(obj):
    '''Removes the @about key from the `obj` dict if that value refers to the
    dict's '@id'
    '''
    about_val = obj.get('@about')
    if about_val:
        id_val = obj.get('@id')
        if id_val and (('#' + id_val) == about_val):
            del obj['@about']

def _add_redundant_about(obj):
    id_val = obj.get('@id')
    if id_val and ('@about' not in obj):
        obj['@about'] = ('#' + id_val)

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
        _LOG.debug('unknown xsi:type "%s"', datatype)
        return None # We'll fall through to here when we encounter types we do not recognize

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
    '''Convert to a BadgerFish-style dict for addition to a dict suitable for
    addition to XML tree or for v1.0 to v0.0 conversion.'''
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

def get_bf_meta_value(d):
    v = d.get('$')
    if v is not None:
        return v
    v = d.get('@content')
    if v is not None:
        return v
    return d.get('@href')

def _contains_hbf_meta_keys(d):
    for k in d.keys():
        if k.startswith('^'):
            return True
    return False

def extract_meta(x):
    try:
        return get_bf_meta_value(x)
    except:
        return None

def find_val_for_first_bf_l_meta(d, prop_name):
    '''Returns the $ value of the first meta element with
    the @property that matches @prop_name (or None).
    '''
    m_list = d.get('meta')
    if not m_list:
        return None
    if not isinstance(m_list, list):
        m_list = [m_list]
    for m_el in m_list:
        if m_el.get('@property') == prop_name:
            return extract_meta(m_el)
    return None

def find_val_for_first_bf_r_meta(d, prop_name):
    '''Returns the $ value of the first meta element with
    the @rel that matches @prop_name (or None).
    '''
    m_list = d.get('meta')
    if not m_list:
        return None
    if not isinstance(m_list, list):
        m_list = [m_list]
    for m_el in m_list:
        if m_el.get('@rel') == prop_name:
            return extract_meta(m_el)
    return None

def find_val_for_first_hbf_l_meta(d, prop_name):
    p = '^' + prop_name
    return d.get(p)

def find_val_literal_meta_first(d, prop_name, version):
    if _is_badgerfish_version(version):
        return find_val_for_first_bf_l_meta(d, prop_name)
    p = '^' + prop_name
    return d.get(p)

def find_nested_meta_first_bf(d, prop_name):
    '''Returns the $ value of the first meta element with
    the @property that matches @prop_name (or None).
    '''
    m_list = d.get('meta')
    if not m_list:
        return None
    if not isinstance(m_list, list):
        m_list = [m_list]
    for m_el in m_list:
        if m_el.get('@property') == prop_name or m_el.get('@rel') == prop_name:
            return m_el
    return None


def find_nested_meta_first(d, prop_name, version):
    '''Returns obj. for badgerfish and val for hbf. Appropriate for nested literals'''
    if _is_badgerfish_version(version):
        return find_nested_meta_first_bf(d, prop_name)
    p = '^' + prop_name
    return d.get(p)

def find_val_resource_meta_first(d, prop_name, version):
    if _is_badgerfish_version(version):
        return find_val_for_first_bf_r_meta(d, prop_name)
    p = '^' + prop_name
    return d.get(p)

def add_literal_meta(obj, prop_name, value, version):
    if _is_badgerfish_version(version):
        m = obj.setdefault('meta', [])
        if not isinstance(m, list):
            m = [m]
            obj['meta'] = m
        d = {'$': value,
                  '@property': prop_name,
                  '@xsi:type': 'nex:LiteralMeta'}
        m.append(d)
        return d
    else:
        k = '^' + prop_name
        _add_value_to_dict_bf(obj, k, value)
        return value

def delete_first_literal_meta(obj, prop_name, version):
    if _is_badgerfish_version(version):
        m = obj.setdefault('meta', [])
        if not isinstance(m, list):
            m = [m]
            obj['meta'] = m
        ind = None
        for n, el in enumerate(m):
            if el.get('@property') == prop_name:
                ind = n
                break
        if ind is not None:
            m.pop(ind)
        if len(m) == 0:
            del obj['meta']
    else:
        k = '^' + prop_name
        if k in obj:
            del obj[k]

def _simplify_object_by_id_del(o):
    if isinstance(o, list):
        return [_simplify_object_by_id_del(i) for i in o]
    if not isinstance(o, dict):
        return o
    if '@id' in o:
        nk = len(o.keys())
        if nk < 3:
            if nk == 1:
                return None
            if '$' in o:
                return o['$']
            if '@href' in o:
                del o['@id']
    return o

def _simplify_all_meta_by_id_del(el):
    to_del = []
    for tag in el.keys():
        if tag.startswith('^'):
            o = el[tag]
            v = _simplify_object_by_id_del(o)
            if v is None:
                to_del.append(tag)
            elif v is not o:
                el[tag] = v
    for tag in to_del:
        del el[tag]
