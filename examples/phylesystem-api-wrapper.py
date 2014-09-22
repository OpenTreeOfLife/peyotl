#!/usr/bin/env python
from peyotl.api import APIWrapper
ps = APIWrapper().phylesystem_api
studies = ps.study_list
print studies[0]
blob = ps.get(studies[0])
nexson = blob['data']['nexml']
print nexson['^ot:studyId'], ':', nexson['^ot:studyPublicationReference']

