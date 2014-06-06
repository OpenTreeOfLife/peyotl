#!/usr/bin/env python
from peyotl.nexson_syntax import write_as_json
from peyotl.utility.io import write_to_filepath
from peyotl.utility import get_config
import requests
import codecs
import anyjson
import json
import os
from peyotl import get_logger
_LOG = get_logger(__name__)

GZIP_REQUEST_HEADERS = {
    'Accept-Encoding' : 'gzip',
    'Content-Type' : 'application/json',
    'Accept' : 'application/json',
}

_JSON_HEADERS = {'Content-Type': 'application/json',
                 'Accept': 'application/json',
                 }

CURL_LOGGER = os.environ.get('PEYOTL_CURL_LOG_FILE')

def escape_dq(s):
    if not (isinstance(s, str) or isinstance(s, unicode)):
        if isinstance(s, bool):
            if s:
                return 'true'
            return 'false'

        return s
    if '"' in s:
        ss = s.split('"')
        return '"{}"'.format('\\"'.join(ss))
    return '"{}"'.format(s)

def log_request_as_curl(curl_log, url, verb, headers, params, data):
    if not curl_log:
        return
    with codecs.open(curl_log, 'a', encoding='utf-8') as curl_fo:
        if headers:
            hargs = ' '.join(['-H {}:{}'.format(escape_dq(k), escape_dq(v)) for k, v in headers.items()])
        else:
            hargs = ''
        if params and not data:
            raise NotImplementedError('log_request_as_curl url encoding')
        if data:
            if isinstance(data, str) or isinstance(data, unicode):
                data = anyjson.loads(data)
            dargs_contents = ', '.join(['{}: {}'.format(escape_dq(k), escape_dq(v)) for k, v in data.items()])
            dargs = "'{" + dargs_contents + "}'"
        else:
            dargs = ''
        curl_fo.write('curl -X {v} {h} {u} --data {d}\n'.format(v=verb,
                                               u=url,
                                               h=hargs,
                                               d=dargs))

class APIDomains(object):
    def __init__(self):
        self._oti = None
        self._phylografter = 'http://www.reelab.net/phylografter'
        self._phylesystem_api = None
        self._taxomachine = None
        self._treemachine = None
    def get_oti(self):
        if self._oti is None:
            self._oti = get_config('apis', 'oti')
            if self._oti is None:
                raise RuntimeError('[apis] / oti config setting required')
        return self._oti
    oti = property(get_oti)
    def get_phylesystem_api(self):
        if self._phylesystem_api is None:
            self._phylesystem_api = get_config('apis', 'phylesystem_api')
            if self._phylesystem_api is None:
                raise RuntimeError('[apis] / phylesystem_api config setting required')
        return self._phylesystem_api
    phylesystem_api = property(get_phylesystem_api)
    def get_phylografter(self):
        return self._phylografter
    phylografter = property(get_phylografter)
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
        self._phylesystem_api = None
        self._taxomachine = None
        self._treemachine = None
        self._oti = None
    def get_oti(self):
        from peyotl.api.oti import _OTIWrapper
        if self._oti is None:
            self._oti = _OTIWrapper(self.domains.oti)
        return self._oti
    oti = property(get_oti)
    def wrap_phylesystem_api(self, **kwargs):
        from peyotl.api.phylesystem_api import _PhylesystemAPIWrapper
        cfrom = get_config('apis', 'phylesystem_get_from', 'local')
        ctrans = get_config('apis', 'phylesystem_transform', 'client').lower()
        crefresh = get_config('apis', 'phylesystem_refresh', 'never').lower()
        kwargs.setdefault('get_from', cfrom)
        kwargs.setdefault('transform', ctrans)
        kwargs.setdefault('refresh', crefresh)
        self._phylesystem_api = _PhylesystemAPIWrapper(self.domains.phylesystem_api, **kwargs)
        return self._phylesystem_api
    def get_phylesystem_api(self):
        if self._phylesystem_api is None:
            self.wrap_phylesystem_api()
        return self._phylesystem_api
    phylesystem_api = property(get_phylesystem_api)
    def get_phylografter(self):
        from peyotl.api.phylografter import _PhylografterWrapper
        if self._phylografter is None:
            self._phylografter = _PhylografterWrapper(self.domains.phylografter)
        return self._phylografter
    phylografter = property(get_phylografter)
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
    fmt = 'error in HTTP {v} verb call to {u} with {p}, {d} and {h}'
    return fmt.format(v=verb, u=url, p=ps, h=hs, d=ds)

_VERB_TO_METHOD_DICT = {
    'GET': requests.get,
    'POST': requests.post,
    'PUT': requests.put
}
class _WSWrapper(object):
    def __init__(self, domain):
        self._domain = domain
    def json_http_get(self, url, headers=_JSON_HEADERS, params=None, text=False):
        return self._do_http(url, 'GET', headers=headers, params=params, data=None, text=text)
    def json_http_put(self, url, headers=_JSON_HEADERS, params=None, data=None, text=False):
        return self._do_http(url, 'PUT', headers=headers, params=params, data=data, text=text)
    def json_http_post(self, url, headers=_JSON_HEADERS, params=None, data=None, text=False):
        return self._do_http(url, 'POST', headers=headers, params=params, data=data, text=text)
    def _do_http(self, url, verb, headers, params, data, text=False):
        if CURL_LOGGER is not None:
            log_request_as_curl(CURL_LOGGER, url, verb, headers, params, data)
        func = _VERB_TO_METHOD_DICT[verb]
        resp = func(url, params=params, headers=headers, data=data)
        try:
            resp.raise_for_status()
        except:
            _LOG.exception(_http_method_summary_str(url, verb, headers, params))
            if resp.text:
                _LOG.debug('HTTPResponse.text = ' + resp.text)
            raise
        if text:
            return resp.text
        return resp.json()
    def get_domain(self):
        return self._domain
    def set_domain(self, d):
        self._domain = d
    domain = property(get_domain, set_domain)
