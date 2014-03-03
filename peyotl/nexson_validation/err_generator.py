#!/usr/bin/env python
'''To save memory, error/warning data is stored as a tuple:
    element 0: MessageTupleAdaptor instance (immutable, shared across all errors/
                    warnings of the same type)
    element 1: python memory address for the object or object reference
    element 2: rich object address (immutable and shared by all instances
                    of warnings for the same object)
    element 3: the "data" argument for the warning. must be hashable.
'''
from peyotl.nexson_validation.warning_codes import NexsonWarningCodes
from cStringIO import StringIO
import codecs

class MessageTupleAdaptor(object):
    '''This base class provides the basic functionality of keeping
    track of the "address" of the element that triggered the warning, 
    the severity code, and methods for writing to free text stream or JSON.
    '''
    def write(self, err_tuple, s, prefix):
        raise NotImplementedError('MessageTupleAdaptor.write')
    def __init__(self):
        self.code = None
    def __unicode__(self, err_tuple, prefix=''):
        b = StringIO()
        ci = codecs.lookup('utf8')
        s = codecs.StreamReaderWriter(b, ci.streamreader, ci.streamwriter)
        self.write(err_tuple, s, prefix)
        return s.getvalue()
    def getvalue(self, err_tuple, prefix=''):
        return self.__unicode__(err_tuple, prefix=prefix)
    def as_dict(self, err_tuple):
        addr = err_tuple[2]
        return {
            'code': NexsonWarningCodes.facets[self.code],
            #'comment': self.__unicode__(err_tuple),
            'data': self.convert_data_for_json(err_tuple),
            'refersTo': addr.path
        }
    def convert_data_for_json(self, err_tuple):
        return err_tuple[3]
    def _write_message_suffix(self, err_tuple, out):
        addr = err_tuple[2]
        addr.write_path_suffix_str(out)

class _StrListDataWarningType(MessageTupleAdaptor):
    '''Adaptor for warning with data being a list of strings
    '''
    def write(self, err_tuple, outstream, prefix):
        data = err_tuple[3]
        ds = '", "'.join(data)
        outstream.write(self.format.format(p=prefix, d=ds))
        self._write_message_suffix(err_tuple, outstream)

class UnrecognizedKeyWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.UNRECOGNIZED_KEY
        self.format = '{p}Unrecognized key(s): "{d}"'
class MissingMandatoryKeyWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MISSING_MANDATORY_KEY
        self.format = '{p}Missing required key(s): "{d}"'

UnrecognizedKeyWarning = UnrecognizedKeyWarningType()
MissingMandatoryKeyWarning = MissingMandatoryKeyWarningType()

def gen_UnrecognizedKeyWarning(addr, pyid, logger, severity, *valist, **kwargs):
    k_list = kwargs['key_list']
    t = (UnrecognizedKeyWarning, pyid, addr, k_list)
    logger.register_new_messages(t, severity=severity)

def gen_MissingMandatoryKeyWarning(addr, pyid, logger, severity, *valist, **kwargs):
    k_list = kwargs['key_list']
    t = (MissingMandatoryKeyWarning, pyid, addr, k_list)
    logger.register_new_messages(t, severity=severity)



factory2code = {}
for k in locals().keys():
    if k.startswith('gen_'):
        obj_n = k[4:]
        if obj_n in locals():
            gf = locals()[k]
            obj = locals()[obj_n]
            factory2code[gf] = obj.code
