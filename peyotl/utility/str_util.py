#!/usr/bin/env python
# python 2 to 3 dealing with unicode....
import sys
if sys.version_info.major == 2:
    from cStringIO import StringIO
    import codecs
    UNICODE = unicode
    def is_str_type(x):
        return isinstance(x, basestring)
    def is_int_type(x):
        return isinstance(x, int) or isinstance(x, long)
    def get_utf_8_string_io_writer():
        string_io = StringIO()
        wrapper = codecs.getwriter("utf8")(string_io)
        return string_io, wrapper
    def flush_utf_8_writer(wrapper):
        wrapper.reset()
    def reverse_dict(d):
        return {v: k for k, v in d.iteritems()}
else:
    from io import StringIO #pylint: disable=E0611,W0403
    UNICODE = str
    def is_str_type(x):
        return isinstance(x, str)
    def is_int_type(x):
        return isinstance(x, int)
    def get_utf_8_string_io_writer():
        string_io = StringIO()
        return string_io, string_io
    flush_utf_8_writer = lambda x: True
    def reverse_dict(d):
        return {v: k for k, v in d.items()}



def underscored2camel_case(v):
    '''converts ott_id to ottId.'''
    vlist = v.split('_')
    c = []
    for n, el in enumerate(vlist):
        if el:
            if n == 0:
                c.append(el)
            else:
                c.extend([el[0].upper(), el[1:]])
    return ''.join(c)
