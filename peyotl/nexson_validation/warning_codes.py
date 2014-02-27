#!/usr/bin/env python
'''Classes for different forms of Warnings and Errors.
'''
from peyotl.nexson_validation.helper import SeverityCodes
# An enum of WARNING_CODES
class NexsonWarningCodes():
    '''Enumeration of Warning/Error types. For internal use.

    NexsonWarningCodes.facets maps int -> warning name.
    Each of these names will also be an attribute of NexsonWarningCodes.
    NexsonWarningCodes.numeric_codes_registered is (after some mild monkey-patching)
        a set of the integers registered.
    '''
    facets = ('MISSING_MANDATORY_KEY',
              'MISSING_OPTIONAL_KEY',
              'UNRECOGNIZED_KEY',
              'MISSING_LIST_EXPECTED',
              'DUPLICATING_SINGLETON_KEY',
              'REFERENCED_ID_NOT_FOUND',
              'REPEATED_ID',
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
class WarningMessage(object):
    '''This base class provides the basic functionality of keeping
    track of the "address" of the element that triggered the warning, 
    the severity code, and methods for writing to free text stream or JSON.
    '''
    def __init__(self,
                 warning_code,
                 data,
                 address,
                 severity=SeverityCodes.WARNING):
        '''
            `warning_code` should be a facet of NexsonWarningCodes
            `data` is an object whose details depend on the specific subclass
                of warning that is being created
            `address` is a NexsonAddress offending element

            `severity` is either SeverityCodes.WARNING or SeverityCodes.ERROR
        '''
        self.warning_code = warning_code
        assert warning_code in NexsonWarningCodes.numeric_codes_registered
        self.warning_data = data
        self.severity = severity
        assert severity in SeverityCodes.numeric_codes_registered
        self.address = address
    def __unicode__(self, prefix=''):
        b = StringIO()
        ci = codecs.lookup('utf8')
        s = codecs.StreamReaderWriter(b, ci.streamreader, ci.streamwriter)
        self.write(s, prefix)
        return s.getvalue()
    def getvalue(self, prefix=''):
        return self.__unicode__(prefix=prefix)
    def as_dict(self):
        return {
            'severity': SeverityCodes.facets[self.severity],
            'code': NexsonWarningCodes.facets[self.warning_code],
            'comment': self.__unicode__(),
            'data': self.convert_data_for_json(),
            'refersTo': self.address.path
        }
    def convert_data_for_json(self):
        wc = self.warning_code
        data = self.warning_data
        return data
    def _write_message_suffix(self, out):
        self.address.write_path_suffix_str(out)

class MissingExpectedListWarning(WarningMessage):
    def __init__(self, data, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.MISSING_LIST_EXPECTED, data=data, address=address, severity=severity)
    def write(self, outstream, prefix):
        outstream.write('{p}Expected a list found "{k}"'.format(p=prefix, k=type(self.data)))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return type(self.data)

class UnrecognizedKeyWarning(WarningMessage):
    def __init__(self, key, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.UNRECOGNIZED_KEY, data=key, address=address, severity=severity)
        self.key = key
    def write(self, outstream, prefix):
        outstream.write('{p}Unrecognized key "{k}"'.format(p=prefix, k=self.key))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.key

class MissingOptionalKeyWarning(WarningMessage):
    def __init__(self, key, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.MISSING_OPTIONAL_KEY, data=key, address=address, severity=severity)
        self.key = key
    def write(self, outstream, prefix):
        if self.key:
            outstream.write('{p}Missing optional key "{k}"'.format(p=prefix, k=self.key))
        else:
            outstream.write('{p}Missing optional key "@property={k}"'.format(p=prefix, k=self.address.property_name)) # MTH hack to get tests to pass
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        if self.key:
            return self.key
        else:
            return "@property={k}".format(k=self.address.property_name) # MTH hack to get tests to pass

class DuplicatingSingletonKeyWarning(WarningMessage):
    def __init__(self, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.DUPLICATING_SINGLETON_KEY, data=None, address=address, severity=severity)
        self.key = address.property_name
    def write(self, outstream, prefix):
        outstream.write('{p}Multiple instances found for a key ("{k}") which was expected to be found once'.format(p=prefix, k=self.key))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.key
class DeprecatedMetaPropertyWarning(WarningMessage):
    def __init__(self, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.DEPRECATED_PROPERTY, data=None, address=address, severity=severity)
        self.key = address.property_name
    def write(self, outstream, prefix):
        outstream.write('{p}Found a deprecated a property ("{k}")'.format(p=prefix, k=self.key))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.key


class RepeatedIDWarning(WarningMessage):
    def __init__(self, identifier, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.REPEATED_ID, data=identifier, address=address, severity=severity)
        self.identifier = identifier
    def write(self, outstream, prefix):
        outstream.write('{p}An ID ("{k}") was repeated'.format(p=prefix, k=self.identifier))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.identifier

class ReferencedIDNotFoundWarning(WarningMessage):
    def __init__(self, key, identifier, address, severity=SeverityCodes.ERROR):
        d = {'key': key, 'value': identifier}
        WarningMessage.__init__(self, NexsonWarningCodes.REFERENCED_ID_NOT_FOUND, data=d, address=address, severity=severity)
        self.key = key
        self.identifier = identifier
    def write(self, outstream, prefix):
        outstream.write('{p}An ID Reference did not match a previous ID ("{k}": "{v}")'.format(p=prefix, k=self.key, v=self.identifier))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.warning_data

class MultipleRootNodesWarning(WarningMessage):
    def __init__(self, nd_id, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.MULTIPLE_ROOT_NODES, data=nd_id, address=address, severity=severity)
        self.nd_id = nd_id
    def write(self, outstream, prefix):
        outstream.write('{p}Multiple nodes in a tree were flagged as being the root node ("{k}" was not the first)'.format(p=prefix, k=self.nd_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.warning_data

class MissingMandatoryKeyWarning(WarningMessage):
    def __init__(self, key, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.MISSING_MANDATORY_KEY, data=key, address=address, severity=severity)
        self.key = key
    def write(self, outstream, prefix):
        outstream.write('{p}Missing required key "{k}"'.format(p=prefix, k=self.key))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.key

class UnrecognizedTagWarning(WarningMessage):
    def __init__(self, tag, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.UNRECOGNIZED_TAG, data=tag, address=address, severity=severity)
        self.tag = tag
    def write(self, outstream, prefix):
        outstream.write(u'{p}Unrecognized value for a tag: "{s}"'.format(p=prefix, s=self.tag))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.tag

class NoRootNodeWarning(WarningMessage):
    def __init__(self, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.NO_ROOT_NODE, data=None, address=address, severity=severity)
    def write(self, outstream, prefix):
        outstream.write('{p}No node in a tree was flagged as being the root node'.format(p=prefix))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None

class MultipleTreesWarning(WarningMessage):
    def __init__(self, trees_list, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.MULTIPLE_TREES, data=trees_list, address=address, severity=severity)
        self.trees_list = trees_list
    def write(self, outstream, prefix):
        outstream.write('{p}Multiple trees were found without an indication of which tree is preferred'.format(p=prefix))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None

class NoTreesWarning(WarningMessage):
    def __init__(self, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.NO_TREES, data=None, address=address, severity=severity)
    def write(self, outstream, prefix):
        outstream.write('{p}No trees were found, or all trees were flagged for deletion'.format(p=prefix))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None

class TipWithoutOTUWarning(WarningMessage):
    def __init__(self, tip_node, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.TIP_WITHOUT_OTU, data=None, address=address, severity=severity)
        self.tip_node = tip_node
    def write(self, outstream, prefix):
        outstream.write('{p}Tip node ("{n}") without a valid @otu value'.format(p=prefix, n=self.tip_node.nexson_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None

class PropertyValueNotUsefulWarning(WarningMessage):
    def __init__(self, value, address, severity=SeverityCodes.WARNING):
        d = {'key': address.property_name, 'value': value}
        WarningMessage.__init__(self, NexsonWarningCodes.PROPERTY_VALUE_NOT_USEFUL, data=d, address=address, severity=severity)
        self.key = address.property_name
        self.value = value
    def write(self, outstream, prefix):
        outstream.write('{p}Unhelpful or deprecated value "{v}" for property "{k}"'.format(p=prefix, k=self.key, v=self.value))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.warning_data

class UnrecognizedPropertyValueWarning(WarningMessage):
    def __init__(self, value, address, severity=SeverityCodes.WARNING):
        d = {'key': address.property_name, 'value': value}
        WarningMessage.__init__(self, NexsonWarningCodes.UNRECOGNIZED_PROPERTY_VALUE, data=d, address=address, severity=severity)
        self.key = address.property_name
        self.value = value
    def write(self, outstream, prefix):
        outstream.write('{p}Unrecognized value "{v}" for property "{k}"'.format(p=prefix, k=self.key, v=self.value))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.warning_data

class InvalidPropertyValueWarning(WarningMessage):
    def __init__(self, value, address, severity=SeverityCodes.ERROR):
        d = {'key': address.property_name, 'value': value}
        WarningMessage.__init__(self, NexsonWarningCodes.INVALID_PROPERTY_VALUE, data=d, address=address, severity=severity)
        self.key = address.property_name
        self.value = value
    def write(self, outstream, prefix):
        outstream.write('{p}Invalid value "{v}" for property "{k}"'.format(p=prefix, k=self.key, v=self.value))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.warning_data

class UnvalidatedAnnotationWarning(WarningMessage):
    def __init__(self, value, address, severity=SeverityCodes.WARNING):
        d = {'key': address.property_name, 'value': value}
        WarningMessage.__init__(self, NexsonWarningCodes.UNVALIDATED_ANNOTATION, data=d, address=address, severity=severity)
        self.key = address.property_name
        self.value = value
    def write(self, outstream, prefix):
        outstream.write(u'{p}Annotation found, but not validated: "{k}" -> "{v}"'.format(p=prefix, k=self.key, v=self.value))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.warning_data

class ConflictingPropertyValuesWarning(WarningMessage):
    def __init__(self, key_value_list, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.CONFLICTING_PROPERTY_VALUES, data=key_value_list, address=address, severity=severity)
        self.key_value_list = key_value_list
    def write(self, outstream, prefix):
        s = u", ".join([u'"{k}"="{v}"'.format(k=i[0], v=i[1]) for i in self.key_value_list])
        outstream.write('{p}Conflicting values for properties: {s}'.format(p=prefix, s=s))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.warning_data

class MultipleTipsMappedToOTTIDWarning(WarningMessage):
    def __init__(self, ott_id, node_list, address, severity=SeverityCodes.WARNING):
        data = {'ott_id':ott_id, 'node_list': node_list}
        WarningMessage.__init__(self, NexsonWarningCodes.MULTIPLE_TIPS_MAPPED_TO_OTT_ID, data=data, address=address, severity=severity)
        self.ott_id = ott_id
        self.node_list = node_list
        self.id_list = [i.nexson_id for i in self.node_list]
        self.id_list.sort()
    def write(self, outstream, prefix):
        s = u', '.join([u'"{i}"'.format(i=i) for i in self.id_list])
        outstream.write('{p}Multiple nodes ({s}) are mapped to the OTT ID "{o}"'.format(p=prefix, 
                                                                                        s=s,
                                                                                        o=self.ott_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return {'nodes': self.id_list}

class NonMonophyleticTipsMappedToOTTIDWarning(WarningMessage):
    def __init__(self, ott_id, clade_list, address, severity=SeverityCodes.WARNING):
        data = {'ott_id':ott_id, 'node_list': clade_list}
        WarningMessage.__init__(self, NexsonWarningCodes.NON_MONOPHYLETIC_TIPS_MAPPED_TO_OTT_ID, data=data, address=address, severity=severity)
        self.ott_id = ott_id
        self.clade_list = clade_list
        sl = [(i[0].nexson_id, i) for i in clade_list]
        sl.sort()
        id_list = []
        for el in sl:
            id_list.append([i.nexson_id for i in el[1]])
        self.id_list = id_list
    def write(self, outstream, prefix):
        str_list = []
        for sub_list in self.id_list:
            s = '", "'.join([str(i) for i in sub_list])
            str_list.append('"{s}"'.format(s=s))
        s = ' +++ '.join([i for i in str_list])
        outstream.write('{p}Multiple nodes that do not form the tips of a clade are mapped to the OTT ID "{o}". The clades are {s}'.format(p=prefix,
                                                                            s=s,
                                                                            o=self.ott_id,
                                                                            ))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return {'nodes': self.id_list}

class TipsWithoutOTTIDWarning(WarningMessage):
    def __init__(self, tip, address, severity=SeverityCodes.WARNING):
        WarningMessage.__init__(self, NexsonWarningCodes.TIP_WITHOUT_OTT_ID, data=tip, address=address, severity=severity)
        self.tip = tip
    def write(self, outstream, prefix):
        outstream.write('{p}Tip node mapped to an OTU ("{o}") which does not have an OTT ID'.format(p=prefix, 
                                                        n=self.tip.nexson_id,
                                                        o=self.tip._otu.nexson_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None

class MultipleEdgesPerNodeWarning(WarningMessage):
    def __init__(self, node, edge, address, severity=SeverityCodes.ERROR):
        data = {'node': node, 'edge': edge}
        WarningMessage.__init__(self, NexsonWarningCodes.MULTIPLE_EDGES_FOR_NODES, data=data, address=address, severity=severity)
        self.node = node
        self.edge = edge
    def write(self, outstream, prefix):
        outstream.write('{p}A node ("{n}") has multiple edges to parents ("{f}" and "{s}")'.format(p=prefix,
                                                                                n=self.node.nexson_id,
                                                                                f=self.node._edge.nexson_id,
                                                                                s=self.edge.nexson_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None

class IncorrectRootNodeLabelWarning(WarningMessage):
    def __init__(self, tagged_node, node_without_parent, address, severity=SeverityCodes.ERROR):
        data = {'tagged': tagged_node, 'node_without_parent': node_without_parent}
        WarningMessage.__init__(self, NexsonWarningCodes.INCORRECT_ROOT_NODE_LABEL, data=data, address=address, severity=severity)
        self.tagged_node = tagged_node
        self.node_without_parent = node_without_parent
    def write(self, outstream, prefix):
        outstream.write('{p}The node flagged as the root ("{t}") is not the node without a parent ("{r}")'.format(p=prefix,
                                                                            t=self.tagged_node.nexson_id,
                                                                            r=self.node_without_parent.nexson_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None

class TreeCycleWarning(WarningMessage):
    def __init__(self, node, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.CYCLE_DETECTED, data=node, address=address, severity=severity)
        self.node = node
    def write(self, outstream, prefix):
        outstream.write('{p}Cycle in a tree detected passing througn node "{n}"'.format(p=prefix, n=self.node.nexson_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.node.nexson_id

class DisconnectedTreeWarning(WarningMessage):
    def __init__(self, root_node_list, address, severity=SeverityCodes.ERROR):
        WarningMessage.__init__(self, NexsonWarningCodes.DISCONNECTED_GRAPH_DETECTED, data=root_node_list, address=address, severity=severity)
        self.root_node_list = root_node_list
    def write(self, outstream, prefix):
        outstream.write('{p}Disconnected graph found instead of tree including root nodes:'.format(p=prefix))
        for index, el in enumerate(self.root_node_list):
            if index ==0:
                outstream.write('"{i}"'.format(i=el.nexson_id))
            else:
                outstream.write(', "{i}"'.format(i=el.nexson_id))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return None
