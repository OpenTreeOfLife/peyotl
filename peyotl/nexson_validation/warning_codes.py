#!/usr/bin/env python
"""Classes for different forms of Warnings and Errors.
"""


# An enum of WARNING_CODES
class NexsonWarningCodes(object):
    """Enumeration of Warning/Error types. For internal use.

    NexsonWarningCodes.facets maps int -> warning name.
    Each of these names will also be an attribute of NexsonWarningCodes.
    NexsonWarningCodes.numeric_codes_registered is (after some mild monkey-patching)
        a set of the integers registered.
    """
    facets = ('MISSING_MANDATORY_KEY',
              'MISSING_OPTIONAL_KEY',
              'UNRECOGNIZED_KEY',
              'MISSING_LIST_EXPECTED',
              'DUPLICATING_SINGLETON_KEY',
              'REFERENCED_ID_NOT_FOUND',
              'REPEATED_ID',
              'REPEATED_OTU',
              'MULTIPLE_ROOT_NODES',
              'NO_ROOT_NODE',
              'MULTIPLE_EDGES_FOR_NODES',
              'CYCLE_DETECTED',
              'DISCONNECTED_GRAPH_DETECTED',
              'INCORRECT_ROOT_NODE_LABEL',
              'TIP_WITHOUT_OTU',
              'TIP_WITHOUT_OTT_ID',
              'MULTIPLE_TIPS_MAPPED_TO_OTT_ID',
              'NON_MONOPHYLETIC_TIPS_MAPPED_TO_OTT_ID',
              'INVALID_PROPERTY_VALUE',
              'PROPERTY_VALUE_NOT_USEFUL',
              'UNRECOGNIZED_PROPERTY_VALUE',
              'MULTIPLE_TREES',
              'UNVALIDATED_ANNOTATION',
              'UNRECOGNIZED_TAG',
              'CONFLICTING_PROPERTY_VALUES',
              'NO_TREES',
              'DEPRECATED_PROPERTY',
              'UNPARSEABLE_META',
              'UNREACHABLE_NODE',
              'INCORRECT_VALUE_TYPE',
              'MISSING_CRUCIAL_CONTENT',
              'MAX_SIZE_EXCEEDED',
              )
    numeric_codes_registered = []


# monkey-patching NexsonWarningCodes...
for _n, _f in enumerate(NexsonWarningCodes.facets):
    setattr(NexsonWarningCodes, _f, _n)
    NexsonWarningCodes.numeric_codes_registered.append(_n)
NexsonWarningCodes.numeric_codes_registered = set(NexsonWarningCodes.numeric_codes_registered)
# End of NexsonWarningCodes enum

################################################################################
# In a burst of over-exuberant OO-coding, MTH added a class for
#   each class of Warning/Error.
#
# Each subclass typically tweaks the writing of the message and the payload
#   that constitutes the "data" blob in the JSON.
################################################################################
# class WarningMessage(object):
#     '''This base class provides the basic functionality of keeping
#     track of the "address" of the element that triggered the warning,
#     the severity code, and methods for writing to free text stream or JSON.
#     '''
#     def __init__(self,
#                  warning_code,
#                  data,
#                  address,
#                  severity=SeverityCodes.WARNING):
#         '''
#             `warning_code` should be a facet of NexsonWarningCodes
#             `data` is an object whose details depend on the specific subclass
#                 of warning that is being created
#             `address` is a NexsonAddress offending element

#             `severity` is either SeverityCodes.WARNING or SeverityCodes.ERROR
#         '''
#         self.warning_code = warning_code
#         assert warning_code in NexsonWarningCodes.numeric_codes_registered
#         self.warning_data = data
#         self.severity = severity
#         assert severity in SeverityCodes.numeric_codes_registered
#         self.address = address
#     def write(self, s, prefix):
#         raise NotImplementedError('WarningMessage.write')
#     def __unicode__(self, prefix=''):
#         b = StringIO()
#         ci = codecs.lookup('utf8')
#         s = codecs.StreamReaderWriter(b, ci.streamreader, ci.streamwriter)
#         self.write(s, prefix)
#         return s.getvalue()
#     def getvalue(self, prefix=''):
#         return self.__unicode__(prefix=prefix)
#     def as_dict(self):
#         return {
#             'severity': SeverityCodes.facets[self.severity],
#             'code': NexsonWarningCodes.facets[self.warning_code],
#             'comment': self.__unicode__(),
#             'data': self.convert_data_for_json(),
#             'refersTo': self.address.path
#         }
#     def convert_data_for_json(self):
#         data = self.warning_data
#         return data
#     def _write_message_suffix(self, out):
#         self.address.write_path_suffix_str(out)
