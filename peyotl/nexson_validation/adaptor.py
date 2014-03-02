#!/usr/bin/env python
'''NexsonValidationAdaptor class.
'''
from cStringIO import StringIO
import datetime
import codecs
import json
import re
from peyotl.nexson_validation.warning_codes import MissingMandatoryKeyWarning, \
                                                   UnrecognizedKeyWarning
from peyotl.nexson_syntax.helper import _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf
from peyotl.nexson_syntax import detect_nexson_version
_NEXEL_TOP_LEVEL = 0
_NEXEL_NEXML = 1
_NEXEL_OTUS = 2
_NEXEL_OTU = 3
_NEXEL_TREES = 4
_NEXEL_TREE = 5
_NEXEL_NODE = 6
_NEXEL_EDGE = 7
_NEXEL_META = 8

_NEXEL_CODE_TO_STR = {
    _NEXEL_TOP_LEVEL: 'top-level container',
    _NEXEL_NEXML: 'nexml element',
    _NEXEL_OTUS: 'otus group',
    _NEXEL_OTU: 'otu',
    _NEXEL_TREES: 'trees group',
    _NEXEL_TREE: 'tree',
    _NEXEL_NODE: 'node',
    _NEXEL_EDGE: 'edge',
    _NEXEL_META: 'meta',
}
class LazyAddress(object):
    @staticmethod
    def _address_code_to_str(code):
        return _NEXEL_CODE_TO_STR[code]
    def __init__(self, code, obj=None, obj_id=None):
        self.code = code
        self.ref = obj
        self.obj_id = obj_id
    def write_path_suffix_str(self, out):
        ts = LazyAddress._address_code_to_str(self.code)
        if self.obj_id is None:
            out.write(' in {t}'.format(t=ts))
        else:
            out.write(' in {t} (id="{i}")'.format(t=ts, i=self.obj_id))
class NexsonValidationAdaptor(object):
    '''An object created during NexSON validation.
    It holds onto the nexson object that it was instantiated for.
    When add_or_replace_annotation is called, it will annotate the 
    nexson object, and when get_nexson_str is called it will
    serialize it.

    This class is useful merely because it allows the validation log
        and annotations to be relatively light weight, and yet easy 
        to efficiently add back to the orignal NexSON object.
    '''
    def __init__(self, obj, logger):
        self._raw = obj
        self._nexml = None
        tlz = None
        for k in obj.keys():
            if k not in ['nexml', 'nex:nexml']:
                if tlz is None:
                    tlz = LazyAddress(_NEXEL_TOP_LEVEL, obj, None)
                logger.warn_event(UnrecognizedKeyWarning, k, address=tlz)
        self._nexml = None
        if ('nexml' not in obj) and ('nex:nexml' not in obj):
            if tlz is None:
                tlz = LazyAddress(NexsonElement.TOP_LEVEL, obj, None)
            logger.error_event(MissingMandatoryKeyWarning, 'nexml', address=tlz)
            return ## EARLY EXIT!!
        self._nexml = obj.get('nexml') or obj['nex:nexml']
        self._nexson_version = detect_nexson_version(obj)
        if _is_by_id_hbf(self._nexson_version):
            self.__class__ = ByIdHBFValidationAdaptor
        elif _is_badgerfish_version(self._nexson_version):
            self.__class__ = BadgerFishValidationAdaptor
        elif _is_direct_hbf(self._nexson_version):
            self.__class__ = DirectHBFValidationAdaptor
        else:
            assert(False) # unrecognized nexson variant
        self._validate_nexml_obj(self._nexml, logger)

    def _validate_nexml_obj(self, nex_obj, logger):
        pass

    def add_or_replace_annotation(self, annotation):
        '''Takes an `annotation` dictionary which is 
        expected to have a string as the value of annotation['author']['name']
        This function will remove all annotations from obj that:
            1. have the same author/name, and
            2. have no messages that are flagged as messages to be preserved (values for 'preserve' that evaluate to true)
        '''
        return # TODO!
        script_name = annotation['author']['name']
        n = obj['nexml']
        former_meta = n.setdefault('meta', [])
        if not isinstance(former_meta, list):
            former_meta = [former_meta]
            n['meta'] = former_meta
        else:
            indices_to_pop = []
            for annotation_ind, el in enumerate(former_meta):
                try:
                    if (el.get('$') == annotation_label) and (el.get('author',{}).get('name') == script_name):
                        m_list = el.get('messages', [])
                        to_retain = []
                        for m in m_list:
                            if m.get('preserve'):
                                to_retain.append(m)
                        if len(to_retain) == 0:
                            indices_to_pop.append(annotation_ind)
                        elif len(to_retain) < len(m_list):
                            el['messages'] = to_retain
                            el['dateModified'] = datetime.datetime.utcnow().isoformat()
                except:
                    # different annotation structures could yield IndexErrors or other exceptions.
                    # these are not the annotations that you are looking for....
                    pass

            if len(indices_to_pop) > 0:
                # walk backwards so pops won't change the meaning of stored indices
                for annotation_ind in indices_to_pop[-1::-1]:
                    former_meta.pop(annotation_ind)
        former_meta.append(annotation)
    def get_nexson_str(self):
        return json.dumps(self._raw, sort_keys=True, indent=0)


class ByIdHBFValidationAdaptor(NexsonValidationAdaptor):
    pass
class DirectHBFValidationAdaptor(NexsonValidationAdaptor):
    pass
class BadgerFishValidationAdaptor(NexsonValidationAdaptor):
    pass