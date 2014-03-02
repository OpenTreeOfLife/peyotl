#!/usr/bin/env python
'''Basic functions and classes which are used by nexson_syntax subpackage,
but do not depend on other parts of peyotl.nexson_syntax
'''
import re
from peyotl.utility import get_logger
_LOG = get_logger(__name__)
# DIRECT_HONEY_BADGERFISH is the closest to BadgerFish
DIRECT_HONEY_BADGERFISH = '1.0.0'
DEFAULT_NEXSON_VERSION = DIRECT_HONEY_BADGERFISH
BY_ID_HONEY_BADGERFISH = '1.2.1'

BADGER_FISH_NEXSON_VERSION = '0.0.0'
NEXML_NEXSON_VERSION = 'nexml'

SUPPORTED_NEXSON_VERSIONS = frozenset([BADGER_FISH_NEXSON_VERSION,
                                       DIRECT_HONEY_BADGERFISH,
                                       BY_ID_HONEY_BADGERFISH])
# TODO: in lieu of real namespace support...
_LITERAL_META_PAT = re.compile(r'.*[:]?LiteralMeta$')
_RESOURCE_META_PAT = re.compile(r'.*[:]?ResourceMeta$')

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

_is_badgerfish_version = lambda x: x.startswith('0.')
_is_direct_hbf = lambda x: x.startswith('1.0.')
_is_by_id_hbf = lambda x: x.startswith('1.2')

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

def _contains_hbf_meta_keys(d):
    for k in d.keys():
        if k.startswith('^'):
            return True
    return False

