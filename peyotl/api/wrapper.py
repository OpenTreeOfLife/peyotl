#!/usr/bin/env python
from cStringIO import StringIO
import datetime
import requests
import json
import gzip
from peyotl import get_logger
_LOG = get_logger(__name__)

_GZIP_REQUEST_HEADERS = {
    'accept-encoding' : 'gzip',
    'content-type' : 'application/json',
    'accept' : 'application/json',
}

class APIDomains(object):
    def __init__(self):
        self.phylografter = 'http://www.reelab.net/phylografter'

def get_domains_obj():
    # hook for config/env-sensitive setting of domains
    api_domains = APIDomains()
    return api_domains

class APIWrapper(object):
    def __init__(self, domains=None):
        if domains is None:
            domains = get_domains_obj()
        self.domains = domains
        self.phylografter = PhylografterWrapper(domains.phylografter)

class PhylografterWrapper(object):
    def __init__(self, domain):
        self.domain = domain

    def get_modified_list(self, since_date="2010-01-01T00:00:00"):
        '''Calls phylografter's modified_list.json to fetch
        a list of all studies that have changed since `since_date`
        `since_date` can be a datetime.datetime object or a isoformat
        string representation of the time.
        '''
        if isinstance(since_date, datetime.datetime):
            since_date = datetime.isoformat(since_date)
        SUBMIT_URI = self.domain + '/study/modified_list.json/url'
        args = {'from': since_date}
        headers = {'content-type': 'application/json'}
        resp = requests.get(SUBMIT_URI, params=args, headers=headers)
        resp.raise_for_status()
        try:
            return resp.json()
        except:
            return resp.json
    
    def get_nexson(self, study_id):
        '''Calls export_gzipNexSON URL and unzips response.
        Raises HTTP error, gzip module error, or RuntimeError
        '''
        if study_id.startswith('pg_'):
            study_id = study_id[3:] #strip pg_ prefix
        SUBMIT_URI = self.domain + '/study/export_gzipNexSON.json/' + study_id
        _LOG.debug('Downloading %s using "%s"\n' % (study_id, SUBMIT_URI))
        resp = requests.get(SUBMIT_URI,
                            headers=_GZIP_REQUEST_HEADERS,
                            allow_redirects=True)
        resp.raise_for_status()
        try:
            uncompressed = gzip.GzipFile(mode='rb',
                                         fileobj=StringIO(resp.content)).read()
            results = uncompressed
        except:
            raise 
        if isinstance(results, unicode) or isinstance(results, str):
            return json.loads(results)
        raise RuntimeError('gzipped response from phylografter export_gzipNexSON.json, but not a string is:', results)
