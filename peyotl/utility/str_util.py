
# python 2 to 3 dealing with unicode....
import sys
if sys.version_info.major == 2:
    from cStringIO import StringIO
    UNICODE = unicode
    def is_str_type(x):
        return isinstance(x, basestring)
    def is_int_type(x):
        return isinstance(x, int) or isinstance(x, long)
    def get_utf_8_string_io_writer():
        string_io = StringIO()
        wrapper = codecs.getwriter("utf8")(string_io)
        return string_io, writer
    def flush_utf_8_writer(wrapper):
        wrapper.reset()
else:
    from io import StringIO
    UNICODE = str
    def is_str_type(x):
        return isinstance(x, str)
    def is_int_type(x):
        return isinstance(x, int)
    def get_utf_8_string_io_writer():
        string_io = StringIO()
        return string_io, string_io
    flush_utf_8_writer = lambda x: True


