#!/usr/bin/env python
from peyotl.nexson_syntax import read_as_json, write_as_json
from peyotl import get_logger

import sys
import re
_LOG = get_logger('evaluate-auto-mapping')
if len(sys.argv) != 3:
    sys.exit('expecting an input file path for the JSON mapping file and output file for the unmapped')
inf = sys.argv[1]
outf = sys.argv[2]
_LOG.debug('Reading test cases from "{}"'.format(inf))
m = read_as_json(inf)


def no_op(orig):
    return [orig]

word_then_cruft = re.compile(r'([A-Z]{3,})[^A-Z]{2,}', re.I)
no_casing_ssp = re.compile(r'([A-Z]{3,})[-_. ]([-a-z]{3,})[-_. ]([a-z]{3,})', re.I)
no_casing_sp = re.compile(r'([A-Z]{3,})[-_. ]([-a-z]{3,})', re.I)
unnamed_sp_term_pat = re.compile(r'([A-Z][a-z]{2,})[-_. ]sp$') 
unnamed_sp_pat = re.compile(r'([A-Z][a-z]{2,})[-_. ]sp[^a-z]') 
var_name_pat = re.compile(r'([A-Z][a-z]{2,})[-_. ]([-a-z]{3,})[-_. ]+var[-_. ]+([a-z]{3,})')
ssp_name_pat = re.compile(r'([A-Z][a-z]{2,})[-_. ]([-a-z]{3,})[-_. ]([-a-z]{3,})')
sp_name_pat = re.compile(r'([A-Z][a-z]{2,})[-_. ]([-a-z]{3,})')
ex_pat = re.compile(r'(.+)[^a-z]ex[^a-z].+')
def cascade_with_ssp_sp_handling(orig):
    m = ex_pat.search(orig)
    if m:
        pre = m.group(1)
        return cascade_with_ssp_sp_handling(pre)
    el = []
    m_list = unnamed_sp_term_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s' % m)
        return el
    m_list = unnamed_sp_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s' % m)
        return el
    m_list = var_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s var. %s' % m)
    m_list = ssp_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s %s' % m)
    m_list = sp_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s' % m)
    else:
        el.append(orig)
    m_list = no_casing_ssp.findall(orig)
    if m_list:
        for m in m_list:
            s = '%s %s %s' % m
            s = s.lower()
            s = s[0].upper() + s[1:]
            el.append(s)
    m_list = no_casing_sp.findall(orig)
    if m_list:
        for m in m_list:
            s = '%s %s' % m
            s = s.lower()
            s = s[0].upper() + s[1:]
            el.append(s)
    m_list = word_then_cruft.findall(orig)
    if m_list:
        for m in m_list:
            s = '%s' % m
            s = s.lower()
            s = s[0].upper() + s[1:]
            el.append(s)
    el.append(orig)
    return el


def case_sensitive_cascade_with_ssp_sp_handling(orig):
    el = []
    m_list = unnamed_sp_term_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s' % m)
        return el
    m_list = unnamed_sp_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s' % m)
        return el
    m_list = ssp_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s %s' % m)
    m_list = sp_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s' % m)
    else:
        el.append(orig)
    return el

def case_sensitive_cascade_with_ssp(orig):
    el = []
    m_list = ssp_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s %s' % m)
    m_list = sp_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s' % m)
    else:
        el.append(orig)
    return el

def case_sensitive(orig):
    el = []
    for m in sp_name_pat.findall(orig):
        el.append('%s %s' % m)
    return el

def case_sensitive_cascade(orig):
    el = []
    m_list = sp_name_pat.findall(orig)
    if m_list:
        for m in m_list:
            el.append('%s %s' % m)
    else:
        el.append(orig)
    return el

def evaluate_strategy_for_study(func, test_case):
    unmatched = []
    num, num_matched = 0, 0
    for el in test_case:
        orig, syns = el
        modified = func(orig)
        matched = False
        for candidate in modified:
            if candidate in syns:
                matched = True
                break
        num += 1
        if matched:
            num_matched += 1
        else:
            unmatched.append(el)
    return num_matched, num, unmatched

def evaluate_strategy(func, name, test_case_dict):
    num, num_matched = 0, 0
    d = {}
    for k, v in test_case_dict.items():
        m, n, u = evaluate_strategy_for_study(func, v)
        if u:
            d[k] = u
        num += n
        num_matched += m
    p = float(num_matched)/float(num)
    _LOG.debug('Strategy "{s}" matched {m} out of {n} which is {p:5.2f}%'.format(s=name,
                                                                           m=num_matched,
                                                                           n=num,
                                                                           p=100*p))
    return num_matched, num, d

num_matched, num, d = evaluate_strategy(no_op, "no_op", m)
num_matched, num, d = evaluate_strategy(case_sensitive, "case sensitive", m)
num_matched, num, d = evaluate_strategy(case_sensitive_cascade, "case sensitive cascade", m)
num_matched, num, d = evaluate_strategy(case_sensitive_cascade_with_ssp, "case sensitive cascade with ssp", m)
num_matched, num, d = evaluate_strategy(case_sensitive_cascade_with_ssp_sp_handling, "case sensitive cascade with ssp + 'sp.' handling", m)
cascade_with_ssp_sp_handling
num_matched, num, d = evaluate_strategy(cascade_with_ssp_sp_handling, 
                                        "full cascade with ssp + 'sp.' handling", m)

write_as_json(d, outf)