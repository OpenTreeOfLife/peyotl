#!/usr/bin/env python
'''Basic functions and classes which are used by nexson_syntax subpackage,
but do not depend on other parts of peyotl.nexson_syntax
'''
# DIRECT_HONEY_BADGERFISH is the closest to BadgerFish
DIRECT_HONEY_BADGERFISH = '1.0.0'
DEFAULT_NEXSON_VERSION = DIRECT_HONEY_BADGERFISH
PREFERRED_HONEY_BADGERFISH = '1.2.0'

BADGER_FISH_NEXSON_VERSION = '0.0.0'
NEXML_NEXSON_VERSION = 'nexml'

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
        self.pristine_if_invalid = conv_cfg.get('pristine_if_invalid', True)

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
_is_legacy_honeybadgerfish = lambda x: x.startswith('1.0.')
_is_by_id_honedybadgerfish = lambda x: x.startswith('1.2')

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
