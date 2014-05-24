#!/usr/bin/env python
from cStringIO import StringIO
from peyotl.utility.io import write_to_filepath
from peyotl.utility import get_config
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

_JSON_HEADERS = {'content-type': 'application/json'}

class APIDomains(object):
    def __init__(self):
        self._phylografter = 'http://www.reelab.net/phylografter'
        self._doc_store = None
    def get_phylografter(self):
        return self._phylografter
    phylografter = property(get_phylografter)
    def get_doc_store(self):
        if self._doc_store is None:
            self._doc_store = get_config('apis', 'doc_store')
            if self._doc_store is None:
                raise RuntimeError('[apis] / doc_store config setting required')
        return self._doc_store
    doc_store = property(get_doc_store)

def get_domains_obj(**kwargs):
    # hook for config/env-sensitive setting of domains
    api_domains = APIDomains()
    return api_domains

class APIWrapper(object):
    def __init__(self, domains=None):
        if domains is None:
            domains = get_domains_obj()
        self.domains = domains
        self._phylografter = None
        self._doc_store = None
    def get_phylografter(self):
        if self._phylografter is None:
            self._phylografter = _PhylografterWrapper(self.domains.phylografter)
        return self._phylografter
    phylografter = property(get_phylografter)
    def get_doc_store(self):
        if self._doc_store is None:
            self._doc_store = _DocStoreAPIWrapper(self.domains.doc_store)
        return self._doc_store
    doc_store = property(get_doc_store)

_CUTOFF_LEN_DETAILED_VIEW = 500
def _dict_summary(d, name):
    dk = d.keys()
    dk.sort()
    sd = unicode(d)
    if len(sd) < _CUTOFF_LEN_DETAILED_VIEW:
        a = []
        for k in dk:
            a.extend([repr(k), ': ', repr(d[k]), ', '])
        return u'%s={%s}' % (name, ''.join(a))
    return u'%s-keys=%s' % (name, repr(dk))

def _http_method_summary_str(url, verb, headers, params):
    ps = _dict_summary(params, 'params')
    hs = _dict_summary(headers, 'headers')
    return 'error in HTTP {v} verb call to {u} with {p} and {h}'.format(v=verb, u=url, p=ps, h=hs)

class _WSWrapper(object):
    def __init__(self, domain):
        self.domain = domain
    def _get(self, url, headers=_JSON_HEADERS, params=None):
        resp = requests.get(url, params=params, headers=headers)
        try:
            resp.raise_for_status()
        except:
            _LOG.exception(_http_method_summary_str(url, 'GET', headers, params))
            raise
        try:
            return resp.json()
        except:
            return resp.json

class _DocStoreAPIWrapper(_WSWrapper):
    def __init__(self, domain):
        _WSWrapper.__init__(self, domain)
    def study_list(self):
        '''Returns a list of strings which are the study IDs'''
        SUBMIT_URI = '{}/study_list'.format(self.domain)
        return self._get(SUBMIT_URI)
    def unmerged_branches(self):
        SUBMIT_URI = '{}/unmerged_branches'.format(self.domain)
        return self._get(SUBMIT_URI)

class _PhylografterWrapper(_WSWrapper):
    def __init__(self, domain):
        _WSWrapper.__init__(self, domain)
    def get_modified_list(self, since_date="2010-01-01T00:00:00", list_only=True):
        '''Calls phylografter's modified_list.json to fetch
        a list of all studies that have changed since `since_date`
        `since_date` can be a datetime.datetime object or a isoformat
        string representation of the time.
        If list_only is True, then the caller will just get the
            list of studies.
        If list_only is False, the method returns the raw response from
          phylografter, which is a dictionary with the keys:
            'from' -> isoformat date stamp
            'studies' -> []
            'to' -> isoformat date stamp

        If `since_date` is specified, it should match the
            '%Y-%m-%dT%H:%M:%S'
        format
        '''
        if isinstance(since_date, datetime.datetime):
            since_date = since_date.strftime('%Y-%m-%dT%H:%M:%S')
        SUBMIT_URI = self.domain + '/study/modified_list.json/url'
        args = {'from': since_date}
        r = self._get(SUBMIT_URI, params=args)
        if list_only:
            return r['studies']
        return r

    def fetch_nexson(self, study_id, output_filepath=None, store_raw=False):
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
            if output_filepath is None:
                return json.loads(results)
            else:
                if store_raw:
                    write_to_filepath(results, output_filepath)
                else:
                    write_as_json()
                return True
        raise RuntimeError('gzipped response from phylografter export_gzipNexSON.json, but not a string is:', results)
    # alias fetch_nexson
    fetch_study = fetch_nexson

def NexsonStore(domains=None):
    return APIWrapper(domains=domains).doc_store

def Phylografter(domains=None):
    return APIWrapper(domains=domains).phylografter
