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
from peyotl.utility import get_logger
from cStringIO import StringIO
import codecs
import json
# monkey patching of NexsonWarningCodes causes lots of warnings
#pylint: disable=E1101
_LOG = get_logger(__name__)

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
            '@code': NexsonWarningCodes.facets[self.code],
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
    def __init__(self):
        self.code = None
        self.format = '{p}'
    def write(self, err_tuple, outstream, prefix):
        data = err_tuple[3]
        ds = '", "'.join(data)
        outstream.write(self.format.format(p=prefix, d=ds))
        self._write_message_suffix(err_tuple, outstream)

class _ArgumentlessWarningType(MessageTupleAdaptor):
    '''Adaptor for warning with data being a list of strings
    '''
    def write(self, err_tuple, outstream, prefix):
        outstream.write(self.format.format(p=prefix))
        self._write_message_suffix(err_tuple, outstream)

class RepeatedOTUWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.REPEATED_OTU
        self.format = '{p}OTU id found in mutliple nodes. id(s): "{d}"'

class UnrecognizedKeyWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.UNRECOGNIZED_KEY
        self.format = '{p}Unrecognized key(s): "{d}"'

class MissingMandatoryKeyWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MISSING_MANDATORY_KEY
        self.format = '{p}Missing required key(s): "{d}"'

class MissingOptionalKeyWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MISSING_OPTIONAL_KEY
        self.format = '{p}Missing optional key(s): "{d}"'

class MissingExpectedListWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MISSING_LIST_EXPECTED
        self.format = '{p}Expected a list for key(s): "{d}"'

class MissingCrucialContentWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MISSING_CRUCIAL_CONTENT
        self.format = '{p}Further validation amd acceptance requires more content; specifically keys(s): "{d}"'

class MultipleRootsWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MULTIPLE_ROOT_NODES
        self.format = '{p}Multiple nodes flagged as the root: "{d}"'

class NoRootWarningType(_ArgumentlessWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MULTIPLE_ROOT_NODES
        self.format = '{p}Multiple nodes flagged as the root:'

class NodeWithMultipleParentsType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.MULTIPLE_EDGES_FOR_NODES
        self.format = '{p} node ID is the target of multiple edges. Node ID(s): "{d}"'

class TreeCycleWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.CYCLE_DETECTED
        self.format = '{p} node ID involved in a cycle in the tree. Node ID(s): "{d}"'

class ReferencedIDNotFoundWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.REFERENCED_ID_NOT_FOUND
        self.format = '{p}An ID reference(s) did not match a previous ID: "{d}"'

class RepeatedIDWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.REPEATED_ID
        self.format = '{p}Object identifier(s) repeated: "{d}"'

class _ObjListDataWarningType(_StrListDataWarningType):
    def convert_data_for_json(self, err_tuple):
        return [json.loads(i) for i in err_tuple[3]]

class UnparseableMetaWarningType(_ObjListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.UNPARSEABLE_META
        self.format = '{p}meta(s) with out @property or @rel: "{d}"'

class UnreachableNodeWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.UNREACHABLE_NODE
        self.format = '{p}Nodes not connected to the root of the tree: "{d}"'
class InvalidKeyWarningType(_StrListDataWarningType):
    def __init__(self):
        self.code = NexsonWarningCodes.INVALID_PROPERTY_VALUE
        self.format = '{p}Invalid or inappropriate key: "{d}"'

class WrongValueTypeWarningType(MessageTupleAdaptor):
    def write(self, err_tuple, outstream, prefix):
        raise NotImplementedError('WrongValueTypeWarningType.write')
    def convert_data_for_json(self, err_tuple):
        rl = []
        for k, v, et in err_tuple[3]:
            rl.append({'key':k, 'type':v, 'expected':et})
        return rl
    def __init__(self):
        MessageTupleAdaptor.__init__(self)
        self.code = NexsonWarningCodes.INCORRECT_VALUE_TYPE
        self.format = '{p}value for key not the expected type: "{d}"'

class MultipleTipsToSameOttIdWarningType(MessageTupleAdaptor):
    def __init__(self):
        MessageTupleAdaptor.__init__(self)
        self.code = NexsonWarningCodes.MULTIPLE_TIPS_MAPPED_TO_OTT_ID
        self.format = '{p}Multiple otus mapping to the same OTT ID used in the same tree: "{d}"'
    def write(self, err_tuple, outstream, prefix):
        raise NotImplementedError('MultipleTipsToSameOttIdWarningType.write')
    def convert_data_for_json(self, err_tuple):
        return [i for i in err_tuple[3]]

# A single, immutable, global instance of each warning type is created

InvalidKeyWarning = InvalidKeyWarningType()
MissingCrucialContentWarning = MissingCrucialContentWarningType()
MissingExpectedListWarning = MissingExpectedListWarningType()
MissingMandatoryKeyWarning = MissingMandatoryKeyWarningType()
MissingOptionalKeyWarning = MissingOptionalKeyWarningType()
MultipleRootsWarning = MultipleRootsWarningType()
MultipleTipsToSameOttIdWarning = MultipleTipsToSameOttIdWarningType()
NodeWithMultipleParents = NodeWithMultipleParentsType()
NoRootWarning = NoRootWarningType()
ReferencedIDNotFoundWarning = ReferencedIDNotFoundWarningType()
RepeatedIDWarning = RepeatedIDWarningType()
RepeatedOTUWarning = RepeatedOTUWarningType()
TreeCycleWarning = TreeCycleWarningType()
UnparseableMetaWarning = UnparseableMetaWarningType()
UnreachableNodeWarning = UnreachableNodeWarningType()
UnrecognizedKeyWarning = UnrecognizedKeyWarningType()
WrongValueTypeWarning = WrongValueTypeWarningType()


def gen_InvalidKeyWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(InvalidKeyWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_MissingCrucialContentWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(MissingCrucialContentWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_MissingExpectedListWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(MissingExpectedListWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_MissingMandatoryKeyWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(MissingMandatoryKeyWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_MissingOptionalKeyWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(MissingOptionalKeyWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_MultipleRootsWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(MultipleRootsWarning, kwargs['node_id_list'], addr, pyid, logger, severity)

def gen_MultipleTipsToSameOttIdWarning(addr, pyid, logger, severity, **kwargs):
    k_list = kwargs['otu_sets']
    k_list.sort()
    k_list = tuple(k_list)
    t = (MultipleTipsToSameOttIdWarning, pyid, addr, k_list)
    logger.register_new_messages(t, severity=severity)

def gen_NodeWithMultipleParents(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(NodeWithMultipleParents, kwargs['node_id_list'], addr, pyid, logger, severity)

def gen_TreeCycleWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(TreeCycleWarning, kwargs['node_id_list'], addr, pyid, logger, severity)

def gen_NoRootWarning(addr, pyid, logger, severity, **kwargs):
    _argumentless_warning(NoRootWarning, addr, pyid, logger, severity)

def gen_ReferencedIDNotFoundWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(ReferencedIDNotFoundWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_RepeatedIDWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(RepeatedIDWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_RepeatedOTUWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(RepeatedOTUWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_UnparseableMetaWarning(addr, pyid, logger, severity, **kwargs):
    _obj_list_warning(UnparseableMetaWarning, kwargs['obj_list'], addr, pyid, logger, severity)

def gen_UnreachableNodeWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(UnreachableNodeWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_UnrecognizedKeyWarning(addr, pyid, logger, severity, **kwargs):
    _key_list_warning(UnrecognizedKeyWarning, kwargs['key_list'], addr, pyid, logger, severity)

def gen_WrongValueTypeWarning(addr, pyid, logger, severity, **kwargs):
    key_val_type_list = tuple([(k, type(v).__name__, t) for k, v, t in kwargs['key_val_type_list']])
    t = (WrongValueTypeWarning, pyid, addr, key_val_type_list)
    logger.register_new_messages(t, severity=severity)


# factory functions that call register_new_messages
def _obj_list_warning(wt, k_list, addr, pyid, logger, severity):
    k_list = tuple([json.dumps(i) for i in k_list])
    t = (wt, pyid, addr, k_list)
    logger.register_new_messages(t, severity=severity)

def _key_list_warning(wt, k_list, addr, pyid, logger, severity):
    k_list.sort()
    k_list = tuple(k_list)
    t = (wt, pyid, addr, k_list)
    #_LOG.debug("t=" + str(t))
    logger.register_new_messages(t, severity=severity)

def _argumentless_warning(wt, addr, pyid, logger, severity):
    t = (wt, pyid, addr, None)
    logger.register_new_messages(t, severity=severity)

# some introspective hacking to create a look up of factory function 2 NexsonWarningCodes type
factory2code = {}
for _local_key in locals().keys():
    if _local_key.startswith('gen_'):
        _obj_n = _local_key[4:]
        if _obj_n in locals():
            _gf = locals()[_local_key]
            _obj = locals()[_obj_n]
            factory2code[_gf] = _obj.code
