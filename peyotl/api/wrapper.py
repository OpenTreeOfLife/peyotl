#!/usr/bin/env python
from cStringIO import StringIO
from peyotl.nexson_syntax import write_as_json
from peyotl.utility.io import write_to_filepath
from peyotl.utility import get_config
import datetime
import requests
import anyjson
import json
import gzip
import os
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
        self._taxomachine = None
        self._treemachine = None
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
    def get_taxomachine(self):
        if self._taxomachine is None:
            self._taxomachine = get_config('apis', 'taxomachine')
            if self._taxomachine is None:
                raise RuntimeError('[apis] / taxomachine config setting required')
        return self._taxomachine
    taxomachine = property(get_taxomachine)
    def get_treemachine(self):
        if self._treemachine is None:
            self._treemachine = get_config('apis', 'treemachine')
            if self._treemachine is None:
                raise RuntimeError('[apis] / treemachine config setting required')
        return self._treemachine
    treemachine = property(get_treemachine)

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
        self._taxomachine = None
        self._treemachine = None
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
    def get_taxomachine(self):
        from peyotl.api.taxomachine import _TaxomachineAPIWrapper
        if self._taxomachine is None:
            self._taxomachine = _TaxomachineAPIWrapper(self.domains.taxomachine)
        return self._taxomachine
    taxomachine = property(get_taxomachine)
    def get_treemachine(self):
        from peyotl.api.treemachine import _TreemachineAPIWrapper
        if self._treemachine is None:
            self._treemachine = _TreemachineAPIWrapper(self.domains.treemachine)
        return self._treemachine
    treemachine = property(get_treemachine)

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

def _http_method_summary_str(url, verb, headers, params, data=None):
    if params is None:
        ps = 'None'
    else:
        ps = _dict_summary(params, 'params')
    hs = _dict_summary(headers, 'headers')
    if data is None:
        ds = 'None'
    elif isinstance(data, str) or isinstance(data, unicode):
        ds = _dict_summary(anyjson.loads(data), 'data')
    else:
        ds = _dict_summary(data, 'data')
    fmt = 'error in HTTP {v} verb call to {u} with {p}, data={d} and {h}'
    return fmt.format(v=verb, u=url, p=ps, h=hs, d=ds)

class _WSWrapper(object):
    def __init__(self, domain):
        self._domain = domain
    def _get(self, url, headers=_JSON_HEADERS, params=None):
        resp = requests.get(url, params=params, headers=headers)
        try:
            resp.raise_for_status()
        except:
            _LOG.exception(_http_method_summary_str(url, 'GET', headers, params))
            if resp.text:
                _LOG.debug('HTTPResponse.text = ' + resp.text)
            raise
        try:
            return resp.json()
        except:
            return resp.json
    def _post(self, url, headers=_JSON_HEADERS, params=None, data=None):
        resp = requests.post(url, params=params, headers=headers, data=data)
        try:
            resp.raise_for_status()
        except:
            _LOG.exception(_http_method_summary_str(url, 'POST', headers=headers, params=params, data=data))
            if resp.text:
                _LOG.debug('HTTPResponse.text = ' + resp.text)
            raise
        try:
            return resp.json()
        except:
            return resp.json
    def _put(self, url, headers=_JSON_HEADERS, params=None, data=None):
        resp = requests.put(url, params=params, headers=headers, data=data)
        try:
            resp.raise_for_status()
        except:
            _LOG.exception(_http_method_summary_str(url, 'PUT', headers=headers, params=params, data=data))
            if resp.text:
                _LOG.debug('HTTPResponse.text = ' + resp.text)
            raise
        try:
            return resp.json()
        except:
            return resp.json
    def get_domain(self):
        return self._domain
    def set_domain(self, d):
        self._domain = d
    domain = property(get_domain, set_domain)

class _DocStoreAPIWrapper(_WSWrapper):
    def __init__(self, domain):
        _WSWrapper.__init__(self, domain)
        self._github_oauth_token = None
    def _get_auth_token(self):
        if self._github_oauth_token is None:
            auth_token = os.environ.get('GITHUB_OAUTH_TOKEN')
            if auth_token is None:
                raise RuntimeError('''To use the write methods of the Open Tree of Life's Nexson document store
you must supply a GitHub OAuth Token. Peyotl uses the GITHUB_OAUTH_TOKEN environmental
variable to obtain this token. If you need to obtain your key, see the instructions at:
   https://github.com/OpenTreeOfLife/api.opentreeoflife.org/tree/master/docs#getting-a-github-oauth-token
''')
            self._github_oauth_token = auth_token
        return self._github_oauth_token
    auth_token = property(_get_auth_token)
    def study_list(self):
        '''Returns a list of strings which are the study IDs'''
        SUBMIT_URI = '{}/study_list'.format(self.domain)
        return self._get(SUBMIT_URI)
    def unmerged_branches(self):
        SUBMIT_URI = '{}/unmerged_branches'.format(self.domain)
        return self._get(SUBMIT_URI)
    def post_study(self,
                   nexson,
                   study_id=None,
                   commit_msg=None):
        assert nexson is not None
        if study_id is None:
            SUBMIT_URI = '{d}/v1/study'.format(d=self.domain)
        else:
            SUBMIT_URI = '{d}/v1/study/{i}'.format(d=self.domain, i=study_id)
        params = {'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self._post(SUBMIT_URI,
                          params=params,
                          data=anyjson.dumps({'nexson': nexson}))
    def put_study(self,
                  study_id,
                  nexson,
                  starting_commit_sha,
                  commit_msg=None):
        assert nexson is not None
        SUBMIT_URI = '{d}/v1/study/{i}'.format(d=self.domain, i=study_id)
        params = {'starting_commit_SHA':starting_commit_sha,
                  'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self._put(SUBMIT_URI,
                         params=params,
                         data=anyjson.dumps({'nexson': nexson}))
    def phylesystem_config(self):
        uri = '{d}/phylesystem_config'.format(d=self.domain)
        return self._get(uri)
    def external_url(self, study_id):
        uri = '{d}/external_url/{i}'.format(d=self.domain, i=study_id)
        return self._get(uri)
    def get_study(self, study_id):
        uri = '{d}/v1/study/{i}'.format(d=self.domain, i=study_id)
        return self._get(uri)

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
        _LOG.debug('Downloading %s using "%s"\n', study_id, SUBMIT_URI)
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

