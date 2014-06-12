#!/usr/bin/env python
from peyotl.api import APIWrapper
from peyotl.nexson_syntax import get_nexml_el, \
                                 read_as_json, \
                                 write_as_json

a = APIWrapper(phylesystem_api_kwargs={'get_from':'local'})
pa = a.phylesystem_api
p = pa.phylesystem_obj
for sid, fp in p.iter_study_filepaths():
    blob = read_as_json(fp)
    nex = get_nexml_el(blob)
    x = nex.get('^ot:studyId')
    if x != sid:
        nex['^ot:studyId'] = sid
        write_as_json(blob, fp)
        print x, sid