#!/usr/bin/env python
'''This script is intended to be installed as cron job.
It will add to a github issue tracker if it notices a
new failure based on the phylesystem-api's push_failure service.
'''
from peyotl.api import PhylesystemAPI
import requests
import codecs
import json
import sys
import os

SCRIPT_DIR = os.path.split(sys.argv[0])[0]
KNOWN_FAILURE_FILE = os.path.join(SCRIPT_DIR, 'known-failed-commits.json')
ORG = 'mtholder'
REPO = 'mephytis'
ISSUE_NUM = 1
URL = "https://api.github.com/repos/{o}/{r}/issues/{i:d}/comments".format(o=ORG, r=REPO, i=ISSUE_NUM)

def read_known_failures():
    if os.path.exists(KNOWN_FAILURE_FILE):
        with codecs.open(KNOWN_FAILURE_FILE, 'r', encoding='utf-8') as kff:
            d = json.load(kff)
    else:
        d = []
    r = {}
    for el in d:
        r[el['commit']] = el
    return r, d

def scream_about_new_failure(resp, OAUTH_TOKEN):
    params = {'access_token': OAUTH_TOKEN}
    template = "A push to GitHub has failed:\n   date: {d}\n   study: {s}\n    commit: {c}"
    msg = template.format(d=resp['date'], s=resp['study'], c=resp['commit'])
    payload = {"body": msg}
    resp = requests.post(URL, params=params, data=json.dumps(payload))
    resp.raise_for_status()

def write_known_failures(fail_list):
    with codecs.open(KNOWN_FAILURE_FILE, 'w', encoding='utf-8') as kff:
        json.dump(fail_list, kff, sort_keys=True, indent=2)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('expecting a GitHub OAUTH token as the first (and only) argument')
    OAUTH_TOKEN = sys.argv[1]
    pa = PhylesystemAPI()
    succeeding, push_fail_dict = pa.push_failure_state
    if not succeeding:
        known_failures_d, kf_list = read_known_failures()
        c = push_fail_dict['commit']
        if c not in known_failures_d:
            scream_about_new_failure(push_fail_dict, OAUTH_TOKEN)
            kf_list.append(push_fail_dict)
            write_known_failures(kf_list)


