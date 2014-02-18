#!/usr/bin/env python
'''Basic functions and classes which are used by nexson_syntax subpackage,
but do not depend on other parts of peyotl.nexson_syntax
'''
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
        prev.append(v)
    else:
        d[k] = [prev, v]
