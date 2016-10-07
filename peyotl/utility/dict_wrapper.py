#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple class to add obj.key syntax to dictionary. This is just syntactic sugar for dictionaries. It is only
used in some API wrappers of peyotl.
Note that the wrappers (even the frozen forms) hold references to the dict used to initialize them.
So, changing that dict will have effects on the wrappers, too.
"""

from peyotl.utility.get_logger import get_logger

_LOG = get_logger('peyotl.utility.dict_wrapper')
_DANGEROUS_KEYS = frozenset(['items', 'values', 'keys', 'get', 'setdefault'])


class DictWrapper(object):
    # pylint: disable=E1101
    def __init__(self, d):
        assert '_raw_dict' not in d  # this would mess up the hacky __getattr__
        for k in _DANGEROUS_KEYS:
            if k in d:
                _LOG.warn('Key "{}" in DictWrapper clashes with a dict member.'.format(k))
        object.__setattr__(self, '_raw_dict', d)

    def __getitem__(self, key):
        return self._raw_dict[key]

    def items(self):
        return self._raw_dict.items()

    def values(self):
        return self._raw_dict.values()

    def keys(self):
        return self._raw_dict.keys()

    def get(self, key, default=None):
        return self._raw_dict.get(key, default=default)

    def setdefault(self, key, default):
        return self._raw_dict.setdefault(key, default)

    def __setitem__(self, key, value):
        self._raw_dict[key] = value

    def __contains__(self, key):
        return key in self._raw_dict

    def __str__(self):
        return '{c}({d})'.format(c=self.__class__.__name__, d=str(self._raw_dict))


class DictAttrWrapper(DictWrapper):
    def __init__(self, d):
        DictWrapper.__init__(self, d)

    def __setattr__(self, key, value):
        self._raw_dict[key] = value

    def __getattr__(self, key):
        try:
            return self._raw_dict[key]
        except:
            raise AttributeError('DictWrapper has no key "{}"'.format(key))


class FrozenDictWrapper(DictWrapper):
    def __init__(self, d):
        DictWrapper.__init__(self, d)

    def __setattr__(self, key, value):
        raise TypeError('A "frozen" class derived from FrozenDictWrapper does not support rebinding keys')

    def __setitem__(self, key, value):
        raise TypeError('A "frozen" class derived from FrozenDictWrapper does not support rebinding keys')


class FrozenDictAttrWrapper(DictAttrWrapper):
    def __init__(self, d):
        DictAttrWrapper.__init__(self, d)

    def __setattr__(self, key, value):
        raise TypeError('A "frozen" class derived from FrozenDictAttrWrapper does not support rebinding keys')

    def __setitem__(self, key, value):
        raise TypeError('A "frozen" class derived from FrozenDictAttrWrapper does not support rebinding keys')
