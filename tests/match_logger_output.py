#!/usr/bin/env python
# -*- coding: utf-8 -*-
"Checks the output from logger_test_messages.py for formatting. First arg is level: simple, raw, or rich "
import sys
import re
LEVEL = ['raw', 'simple', 'rich'].index(sys.argv[1])


'''expected exception
Traceback (most recent call last):
  File "tests/logger_test_messages.py", line 9, in <module>
    raise RuntimeError("A testing runtime error")
RuntimeError: A testing runtime error

[03:07:00] logger_test_messages.py (3):    DEBUG: a debug message
[03:07:00] logger_test_messages.py (4):     INFO: an info message
[03:07:00] logger_test_messages.py (5):  WARNING: a warning message
[03:07:00] logger_test_messages.py (6):    ERROR: an error message
[03:07:00] logger_test_messages.py (7): CRITICAL: a critical message
[03:07:00] logger_test_messages.py (11):    ERROR: expected exception
'''
level_message = r'\s*([A-Z]+):\s+(\S.*)$'
simple_line_pat = re.compile('^' + level_message)
rich_line_pat = re.compile(r'^\[[0-9:]+\]\s+logger_test_messages.py\s+\(\d+\):' + level_message)
raw_message_pat = re.compile(r'^a.*message\s*$')
except_message_pat = re.compile(r'^\s*expected exception\s*$')
def check_message(message):
    if raw_message_pat.match(message) or except_message_pat.match(message):
        return True

line_pattern = rich_line_pat if LEVEL == 2 else simple_line_pat
def check_line(line):
    if LEVEL == 0:
        message = line
    else:
        m = line_pattern.match(line)
        if not m:
            raise RuntimeError('Line "{}" does not match formatter.'.format(line[:-1]))
        mlevel = m.group(1)
        if mlevel not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise RuntimeError('Line leve "{}" does not match formatter.'.format(mlevel))
        message = m.group(2)
    if check_message(message):
        return
    raise RuntimeError('Unexpected message "{}" in logger output.'.format(line[:-1]))


def check_file(inp):
    in_traceback = False
    for line in inp:
        if in_traceback:
            if line.startswith('  File') or line.startswith('    raise'):
                pass
            elif line.startswith('RuntimeError'):
                in_traceback = False
            else:
                raise RuntimeError('Unexpected "{}" in traceback part of log'.format(line[:-1]))
        elif line.startswith('Traceback'):
            in_traceback = True
        else:
            check_line(line)
for f in sys.argv[2:]:
    with open(f, 'rU') as inp:
        check_file(inp)