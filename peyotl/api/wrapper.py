#!/usr/bin/env python
from peyotl.nexson_syntax import write_as_json
from peyotl.utility.io import write_to_filepath
from peyotl.utility import get_config
import requests
import anyjson
import json
import os
from peyotl import get_logger
_LOG = get_logger(__name__)

GZIP_REQUEST_HEADERS = {
    'accept-encoding' : 'gzip',
    'content-type' : 'application/json',
    'accept' : 'application/json',
}

_JSON_HEADERS = {'content-type': 'application/json'}

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
    def get_phylesystem_api(self):
        from peyotl.api.phylesystem_api import _PhylesystemAPIWrapper
        if self._phylesystem_api is None:
            self._phylesystem_api = _PhylesystemAPIWrapper(self.domains.phylesystem_api)
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
        # _LOG.debug('POSTing:\n' + _http_method_summary_str(url, 'PUT', headers=headers, params=params, data=data))
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
