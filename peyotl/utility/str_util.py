
# python 2 to 3 dealing with unicode....
import sys
if sys.version_info.major == 2:
    UNICODE = unicode
    def is_str_type(x):
        return isinstance(x, str) or isinstance(x, unicode)
else:
    UNICODE = str
    def is_str_type(x):
        return isinstance(x, str)
