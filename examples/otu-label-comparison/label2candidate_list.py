#!/usr/bin/env python
from peyotl.nexson_syntax import write_as_json
import json
import sys
import re
cf_pat = re.compile(r'([A-Z]{3,})[^a-z]cf[^a-z]([A-Z]{3,})[^a-z]?([A-Z]*)', re.I)
aff_pat = re.compile(r'([A-Z]{3,})[^a-z]aff[^a-z]([A-Z]{3,})[^a-z]?([A-Z]*)', re.I)
word_then_punc = re.compile(r'([A-Z]{3,})[.]', re.I)
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
    el = [orig]
    m = ex_pat.search(orig)
    if m:
        pre = m.group(1)
        return [orig] + cascade_with_ssp_sp_handling(pre)
    m = cf_pat.search(orig)
    if m:
        if m.group(3):
            el.append('%s cf. %s %s' % m.groups())
        else:
            el.append('%s cf. %s' % (m.group(1), m.group(2)))
        el.append(m.group(1))
    m = aff_pat.search(orig)
    if m:
        if m.group(3):
            el.append('%s aff. %s %s' % m.groups())
        else:
            el.append('%s aff. %s' % (m.group(1), m.group(2)))
        el.append(m.group(1))
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
    m_list = word_then_punc.findall(orig)
    if m_list:
        for m in m_list:
            s = '%s' % m
            s = s.lower()
            s = s[0].upper() + s[1:]
            el.append(s)
    el.append(orig)
    return el

def find_ott_matches(word):
    w_list = cascade_with_ssp_sp_handling(word)
    r_set = set()
    u_list = []
    for w in w_list:
        if w not in r_set:
            r_set.add(w)
            u_list.append(w)
    from peyotl.sugar import taxomachine
    return taxomachine.TNRS(u_list)
for word in sys.argv[1:]:
    r = find_ott_matches(word)
    write_as_json(r, sys.stdout, indent=1)