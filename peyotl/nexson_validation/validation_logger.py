#!/usr/bin/env python
'''Classes for recording warnings and errors
'''
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
            self.registered = set(WarningCodes.numeric_codes_registered)
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
