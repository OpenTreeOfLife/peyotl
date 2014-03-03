#!/usr/bin/env python
'''Classes for recording warnings and errors
'''
from peyotl.nexson_validation.helper import SeverityCodes, VERSION
from peyotl.nexson_validation.warning_codes import NexsonWarningCodes
import datetime
import platform
import uuid
import sys

def _err_warn_summary(w):
    d = {}
    for el in w:
        msg_adapt_inst = el[0]
        r = msg_adapt_inst.as_dict(el)
        key = r['code']
        del r['code']
        d[key] = r
    return d

class DefaultRichLogger(object):
    def __init__(self, store_messages=False):
        self.out = sys.stderr
        self.store_messages_as_obj = store_messages
        self._warn_by_type = {}
        self._err_by_type = {}
        self._warn_by_obj = {}
        self._err_by_obj = {}
        self.prefix = ''
        self.retain_deprecated = False
        self.codes_to_skip = set()
    def get_errors(self):
        return self._err_by_type.values()
    errors = property(get_errors)
    def get_warnings(self):
        return self._warn_by_type.values()
    warnings = property(get_warnings)
    def is_logging_type(self, t):
        #pylint: disable=W0613,R0201
        return True
    def register_new_messages(self, err_tup, severity):
        c = err_tup[0].code
        pyid = err_tup[1]
        if severity == SeverityCodes.WARNING:
            x = self._warn_by_type.setdefault(c, set())
            x.add(err_tup)
            x = self._warn_by_obj.setdefault(pyid, set())
            x.add(err_tup)
        else:
            x = self._err_by_type.setdefault(c, set())
            x.add(err_tup)
            x = self._err_by_obj.setdefault(pyid, set())
            x.add(err_tup)
    
    def get_err_warn_summary_dict(self):
        w = {}
        for wm in self._warn_by_type.values():
            d = _err_warn_summary(wm)
            w.update(d)
        e = {}
        for em in self._err_by_type.values():
            d = _err_warn_summary(em)
            e.update(d)
        return {'warnings': w, 'errors': e}

    def prepare_annotation(self, 
                       author_name='',
                       invocation=tuple(),
                       annotation_label='',
                       author_version=VERSION,
                       url='https://github.com/OpenTreeOfLife/api.opentreeoflife.org',
                       description=None
                       ):
        if description is None:
            description = "validator of NexSON constraints as well as constraints "\
                          "that would allow a study to be imported into the Open Tree "\
                          "of Life's phylogenetic synthesis tools"
        checks_performed = list(NexsonWarningCodes.numeric_codes_registered)
        for code in self.codes_to_skip:
            try:
                checks_performed.remove(code)
            except:
                pass
        checks_performed = [NexsonWarningCodes.facets[i] for i in checks_performed]
        nuuid = 'meta-' + str(uuid.uuid1())
        annotation = {
            '@property': 'ot:annotation',
            '$': annotation_label,
            '@xsi:type': 'nex:ResourceMeta',
            'author': {
                'name': author_name, 
                'url': url, 
                'description': description,
                'version': author_version,
                'invocation': {
                    'commandLine': invocation,
                    'checksPerformed': checks_performed,
                    'pythonVersion' : platform.python_version(),
                    'pythonImplementation' : platform.python_implementation(),
                }
            },
            'dateCreated': datetime.datetime.utcnow().isoformat(),
            'id': nuuid,
            'messages': [],
            'isValid': (len(self.errors) == 0) and (len(self.warnings) == 0),
        }
        message_list = annotation['messages']
        return annotation
        for m in self.errors:
            d = m.as_dict()
            d['severity'] = 'ERROR'
            d['preserve'] = False
            message_list.append(d)
        for m in self.warnings:
            d = m.as_dict()
            d['severity'] = 'WARNING'
            d['preserve'] = False
            message_list.append(d)
        return annotation


class ValidationLogger(DefaultRichLogger):
    def __init__(self, store_messages=False):
        DefaultRichLogger.__init__(self, store_messages=store_messages)

class FilteringLogger(ValidationLogger):
    def __init__(self, codes_to_register=None, codes_to_skip=None, store_messages=False):
        ValidationLogger.__init__(self, store_messages=store_messages)
        self.codes_to_skip = set()
        if codes_to_register:
            self.registered = set(codes_to_register)
            if codes_to_skip:
                for el in codes_to_skip:
                    self.codes_to_skip.add(el)
                    assert el not in self.registered
        else:
            assert codes_to_skip
            self.registered = set(NexsonWarningCodes.numeric_codes_registered)
            for el in codes_to_skip:
                self.codes_to_skip.add(el)
                self.registered.remove(el)
    def is_logging_type(self, t):
        return (t not in self.codes_to_skip) and (t in self.registered)
