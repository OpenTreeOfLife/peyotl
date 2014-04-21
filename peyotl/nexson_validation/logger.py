#!/usr/bin/env python
'''Classes for recording warnings and errors
'''
from peyotl.nexson_syntax.helper import _add_value_to_dict_bf
from peyotl.nexson_validation.helper import SeverityCodes, VERSION
from peyotl.nexson_validation.warning_codes import NexsonWarningCodes
from peyotl.utility import get_logger
_LOG = get_logger(__name__)
import platform
import sys

def _err_warn_summary(w):
    d = {}
    for el in w:
        msg_adapt_inst = el[0]
        r = msg_adapt_inst.as_dict(el)
        key = r['@code']
        del r['@code']
        _add_value_to_dict_bf(d, key, r)
    return d

def _create_message_list(key, w, severity):
    d = []
    for el in w:
        msg_adapt_inst = el[0]
        r = msg_adapt_inst.as_dict(el)
        r['@severity'] = severity
        d.append(r)
    return d

_LIST_0 = [0]
_LIST_1 = [1]
def _msg_data_cmp(x, y):
    return cmp(x.get('data', _LIST_0), y.get('data', _LIST_1))

def _msg_cmp(x, y):
    xr = x.get('refersTo')
    yr = y.get('refersTo')
    if xr is None:
        if yr is None:
            return _msg_data_cmp(x, y)
        else:
            return 1
    if yr is None:
        return -1
    xri = xr.get('@idref')
    yri = yr.get('@idref')
    #_LOG.debug('xri = "{x}" yri = "{y}"'.format(x=xri, y=yri))
    if xri is None:
        if yri is None:
            xrk = xr.keys()
            xrk.sort()
            yrk = yr.keys()
            yrk.sort()
            r = cmp(xrk, yrk)
            if r == 0:
                xrv = [xr[i] for i in xrk]
                yrv = [yr[i] for i in xrk]
                c = cmp(xrv, yrv)
                if c == 0:
                    return _msg_data_cmp(x, y)
                return c
            return r
        return 1
    if yri is None:
        return -1
    r = cmp(xri, yri)
    if r != 0:
        return r
    return _msg_data_cmp(x, y)

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
    def has_error(self):
        return bool(self._err_by_type)
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

    def get_err_warn_summary_dict(self, sort=True):
        w = {}
        for wm in self._warn_by_type.values():
            d = _err_warn_summary(wm)
            w.update(d)
        e = {}
        for em in self._err_by_type.values():
            d = _err_warn_summary(em)
            e.update(d)
        if sort:
            for v in w.values():
                if isinstance(v, list):
                    v.sort(cmp=_msg_cmp)
            for v in e.values():
                if isinstance(v, list):
                    v.sort(cmp=_msg_cmp)
        return {'warnings': w, 'errors': e}

    def create_nexson_message_list(self, sort=True):
        em_list = []
        for key, em in self._err_by_type.items():
            d = _create_message_list(key, em, 'ERROR')
            em_list.extend(d)
        if sort:
            em_list.sort(cmp=_msg_cmp)
        wm_list = []
        for key, em in self._warn_by_type.items():
            d = _create_message_list(key, em, 'WARNING')
            wm_list.extend(d)
        if sort:
            em_list.sort(cmp=_msg_cmp)
            wm_list.sort(cmp=_msg_cmp)
        em_list.extend(wm_list)
        return em_list


    def prepare_annotation(self,
                       author_name='',
                       invocation=tuple(),
                       author_version=VERSION,
                       url='https://github.com/OpenTreeOfLife/peyotl',
                       description=None,
                       annotation_label=None #@TEMP arg for backward compat.
                       ):
        if description is None:
            description = "validator of NexSON constraints as well as constraints "\
                          "that would allow a study to be imported into the Open Tree "\
                          "of Life's phylogenetic synthesis tools"
        #@TEMP. the args are in flux between the branches of api.opentreeoflife.org.
        #    which is bad. Hopefully we don't need annotation_label and
        #   can get rid of it.
        if annotation_label is not None:
            description += annotation_label
        checks_performed = list(NexsonWarningCodes.numeric_codes_registered)
        for code in self.codes_to_skip:
            try:
                checks_performed.remove(code)
            except:
                pass
        checks_performed = [NexsonWarningCodes.facets[i] for i in checks_performed]
        agent_id = 'peyotl-validator'
        aevent_id = agent_id + '-event'
        ml = self.create_nexson_message_list()
        annotation = {
            '@id': aevent_id,
            '@description': description,
            '@wasAssociatedWithAgentId': agent_id,
            #'@dateCreated': datetime.datetime.utcnow().isoformat(),
            '@passedChecks': not self.has_error(),
            '@preserve': False,
            'message': ml
        }
        invocation_obj = {
            'commandLine': invocation,
            'checksPerformed': checks_performed,
            'otherProperty': [
                {'name': 'pythonVersion',
                'value': platform.python_version()},
                {'name': 'pythonImplementation',
                'value': platform.python_implementation(),
                },
            ]
        }
        agent = {
            '@id': agent_id,
            '@name': author_name,
            '@url': url,
            '@description': description,
            '@version': author_version,
            'invocation': invocation_obj,
        }
        return {'annotationEvent': annotation, 'agent': agent}


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
