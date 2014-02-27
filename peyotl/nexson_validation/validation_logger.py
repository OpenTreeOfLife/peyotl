#!/usr/bin/env python
'''Classes for recording warnings and errors
'''
from peyotl.nexson_validation.helper import SeverityCodes, VERSION

class DefaultRichLogger(object):
    def __init__(self, store_messages=False):
        self.out = sys.stderr
        self.store_messages_as_obj = store_messages
        self.warnings = []
        self.errors = []
        self.prefix = ''
        self.retain_deprecated = False
    def warn(self, warning_code, data, address):
        m = WarningMessage(warning_code, data, address, severity=SeverityCodes.WARNING)
        self.warning(m)
    def warning(self, m):
        if self.store_messages_as_obj:
            self.warnings.append(m)
        else:
            m.write(self.out, self.prefix)
    def error(self, warning_code, address, subelement=''):
        m = WarningMessage(warning_code, data, address)
        self.emit_error(m)
    def emit_error(self, m):
        m.severity = SeverityCodes.ERROR
        if self.store_messages_as_obj:
            self.errors.append(m)
        else:
            raise NexSONError(m.getvalue(self.prefix))
    def prepare_annotation(self, 
                       author_name='',
                       invocation=tuple(),
                       annotation_label='',
                       author_version=VERSION,
                       url='https://github.com/OpenTreeOfLife/api.opentreeoflife.org',
                       description="validator of NexSON constraints as well as constraints that would allow a study to be imported into the Open Tree of Life's phylogenetic synthesis tools"
                       ):
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
    def warning(self, m):
        if not self.store_messages_as_obj:
            m = m.getvalue(self.prefix)
        self.warnings.append(m)
    def emit_error(self, m):
        m.severity = SeverityCodes.ERROR
        if not self.store_messages_as_obj:
            m = m.getvalue(self.prefix)
        self.errors.append(m)

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

    def warning(self, m):
        if m.warning_code in self.codes_to_skip:
            return
        if m.warning_code in self.registered:
            ValidationLogger.warning(self, m)
    def emit_error(self, m):
        m.severity = SeverityCodes.ERROR
        if m.warning_code in self.codes_to_skip:
            return
        if m.warning_code in self.registered:
            ValidationLogger.emit_error(self, m)
