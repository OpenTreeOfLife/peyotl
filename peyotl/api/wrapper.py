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
                 'Accept': 'application/json', }

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
            import urllib
            url = url + '?' + urllib.urlencode(params)
            dargs = ''
        if data:
            if isinstance(data, str) or isinstance(data, unicode):
                data = anyjson.loads(data)
            dargs = "'" + anyjson.dumps(data) + "'"
        else:
            dargs = ''
        data_arg = ''
        if dargs:
            data_arg = ' --data {d}'.format(d=dargs)
        curl_fo.write('curl -X {v} {h} {u}{d}\n'.format(v=verb,
                                                        u=url,
                                                        h=hargs,
                                                        d=data_arg))

class APIDomains(object):
    def __init__(self, **kwargs):
        self._oti = kwargs.get('oti')
        self._phylografter = 'http://www.reelab.net/phylografter'
        self._phylesystem_api = kwargs.get('phylesystem')
        self._taxomachine = kwargs.get('taxomachine')
        self._treemachine = kwargs.get('treemachine')
    def get_oti(self):
        if self._oti is None:
            self._oti = get_config('apis', 'oti')
            if self._oti is None:
                self._oti = 'http://api.opentreeoflife.org'
            #_LOG.debug('using  "{u}" for {s}'.format(u=self._oti, s='oti'))
        return self._oti
    oti = property(get_oti)
    def get_phylesystem_api(self):
        if self._phylesystem_api is None:
            self._phylesystem_api = get_config('apis', 'phylesystem_api')
            if self._phylesystem_api is None:
                self._phylesystem_api = 'http://api.opentreeoflife.org'
            #_LOG.debug('using "{u}" for {s}'.format(u=self._phylesystem_api, s='phylesystem'))
        return self._phylesystem_api
    phylesystem_api = property(get_phylesystem_api)
    def get_phylografter(self):
        return self._phylografter
    phylografter = property(get_phylografter)
    def get_taxomachine(self):
        if self._taxomachine is None:
            self._taxomachine = get_config('apis', 'taxomachine')
            if self._taxomachine is None:
                self._taxomachine = 'http://api.opentreeoflife.org'
            #_LOG.debug('using "{u}" for {s}'.format(u=self._taxomachine, s='taxomachine'))
        return self._taxomachine
    taxomachine = property(get_taxomachine)
    def get_treemachine(self):
        if self._treemachine is None:
            self._treemachine = get_config('apis', 'treemachine')
            if self._treemachine is None:
                self._treemachine = 'http://api.opentreeoflife.org'
            #_LOG.debug('using "{u}" for {s}'.format(u=self._treemachine, s='treemachine'))
        return self._treemachine
    treemachine = property(get_treemachine)

def get_domains_obj(**kwargs):
    # hook for config/env-sensitive setting of domains
    api_domains = APIDomains(**kwargs)
    return api_domains

class APIWrapper(object):
    def __init__(self, domains=None, phylesystem_api_kwargs=None, **kwargs):
        if domains is None:
            domains = get_domains_obj(**kwargs)
        self.domains = domains
        self._phylografter = None
        self._phylesystem_api = None
        self._taxomachine = None
        self._treemachine = None
        self._oti = None
        self._tree_of_life_wrapper = None
        self._graph_wrapper = None
        self._taxonomy_wrapper = None
        self._tnrs_wrapper = None
        self._studies_wrapper = None
        self._study_wrapper = None
        if phylesystem_api_kwargs is None:
            self._phylesystem_api_kwargs = {}
        else:
            self._phylesystem_api_kwargs = dict(phylesystem_api_kwargs)
    def get_oti(self):
        from peyotl.api.oti import _OTIWrapper
        if self._oti is None:
            self._oti = _OTIWrapper(self.domains.oti)
        return self._oti
    oti = property(get_oti)
    def wrap_phylesystem_api(self, **kwargs):
        from peyotl.api.phylesystem_api import _PhylesystemAPIWrapper
        cfrom = get_config('apis', 
                           'phylesystem_get_from',
                           self._phylesystem_api_kwargs.get('get_from'))
        ctrans = get_config('apis',
                            'phylesystem_transform',
                            self._phylesystem_api_kwargs.get('transform'))
        crefresh = get_config('apis',
                              'phylesystem_refresh',
                              self._phylesystem_api_kwargs.get('refresh'))
        if cfrom:
            kwargs.setdefault('get_from', cfrom)
        if ctrans:
            kwargs.setdefault('transform', ctrans)
        if crefresh:
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
    def get_tree_of_life_wrapper(self):
        if self._tree_of_life_wrapper is None:
            self._tree_of_life_wrapper = _TreeOfLifeServicesWrapper(self.treemachine)
        return self._tree_of_life_wrapper
    tree_of_life = property(get_tree_of_life_wrapper)
    def get_graph_wrapper(self):
        if self._graph_wrapper is None:
            self._graph_wrapper = _GraphOfLifeServicesWrapper(self.treemachine)
        return self._graph_wrapper
    graph = property(get_graph_wrapper)
    def get_study_wrapper(self):
        if self._study_wrapper is None:
            self._study_wrapper = _StudyServicesWrapper(self.phylesystem_api)
        return self._study_wrapper
    study = property(get_study_wrapper)
    def get_tnrs_wrapper(self):
        if self._tnrs_wrapper is None:
            self._tnrs_wrapper = _TNRSServicesWrapper(self.taxomachine)
        return self._tnrs_wrapper
    tnrs = property(get_tnrs_wrapper)
    def get_taxonomy_wrapper(self):
        if self._taxonomy_wrapper is None:
            self._taxonomy_wrapper = _TaxonomyServicesWrapper(self.taxomachine)
        return self._taxonomy_wrapper
    taxonomy = property(get_taxonomy_wrapper)
    def get_studies_wrapper(self):
        if self._studies_wrapper is None:
            self._studies_wrapper = _StudiesServicesWrapper(self.oti)
        return self._studies_wrapper
    studies = property(get_studies_wrapper)

class _StudiesServicesWrapper(object):
    def __init__(self, oti_wrapper):
        self.oti = oti_wrapper
    def find_studies(self, *valist, **kwargs):
        return self.oti.find_studies(*valist, **kwargs)
    def find_trees(self, *valist, **kwargs):
        return self.oti.find_trees(*valist, **kwargs)
    def properties(self):
        return self.oti.search_terms
class _TNRSServicesWrapper(object):
    def __init__(self, taxomachine_wrapper):
        self.taxomachine = taxomachine_wrapper
    def match_names(self, *valist, **kwargs):
        return self.taxomachine.TNRS(*valist, **kwargs)
    def autocomplete_name(self, *valist, **kwargs):
        return self.taxomachine.autocomplete(*valist, **kwargs)
    def contexts(self, *valist, **kwargs):
        return self.taxomachine.contexts(*valist, **kwargs)
class _TaxonomyServicesWrapper(object):
    def __init__(self, taxomachine_wrapper):
        self.taxomachine = taxomachine_wrapper
    def about(self, *valist, **kwargs):
        return self.taxomachine.about(*valist, **kwargs)
    info = about
    def lica(self, *valist, **kwargs):
        return self.taxomachine.lica(*valist, **kwargs)
    def subtree(self, *valist, **kwargs):
        return self.taxomachine.subtree(*valist, **kwargs)
    def taxon(self, *valist, **kwargs):
        return self.taxomachine.taxon(*valist, **kwargs)
class _TNRSServicesWrapper(object):
    def __init__(self, taxomachine_wrapper):
        self.taxomachine = taxomachine_wrapper
    def match_names(self, *valist, **kwargs):
        return self.taxomachine.TNRS(*valist, **kwargs)
    def autocomplete_name(self, *valist, **kwargs):
        return self.taxomachine.autocomplete(*valist, **kwargs)
    def contexts(self, *valist, **kwargs):
        return self.taxomachine.contexts(*valist, **kwargs)
    def infer_context(self, *valist, **kwargs):
        return self.taxomachine.infer_context(*valist, **kwargs)
class _StudyServicesWrapper (object):
    def __init__(self, phylesystem_api):
        self.phylesytem_wrapper = phylesystem_api
    def get(self, *valist, **kwargs):
        return self.phylesytem_wrapper.get(*valist, **kwargs)
class _GraphOfLifeServicesWrapper(object):
    def __init__(self, treemachine_wrapper):
        self.treemachine = treemachine_wrapper
    def info(self):
        return self.treemachine.get_graph_info()
    about = info
    def source_tree(self, *valist, **kwargs):
        return self.treemachine.get_source_tree(*valist, **kwargs)
    def node_info(self, *valist, **kwargs):
        return self.treemachine.node_info(*valist, **kwargs)
class _TreeOfLifeServicesWrapper(object):
    def __init__(self, treemachine_wrapper):
        self.treemachine = treemachine_wrapper
    def info(self):
        return self.treemachine.get_synthetic_tree_info()
    about = info
    def mrca(self, *valist, **kwargs):
        return self.treemachine.mrca(*valist, **kwargs)
    def subtree(self, *valist, **kwargs):
        return self.treemachine.get_synthetic_tree(*valist, **kwargs)
    def induced_subtree(self, *valist, **kwargs):
        return self.treemachine.induced_subtree(*valist, **kwargs)
    induced_tree = induced_subtree

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
    def json_http_post_raise(self, url, headers=_JSON_HEADERS, params=None, data=None, text=False):
        r = self.json_http_post(url, headers=headers, params=params, data=data, text=text)
        if 'error' in r:
            raise ValueError(r['error'])
        return r
    def _do_http(self, url, verb, headers, params, data, text=False):
        if CURL_LOGGER is not None:
            log_request_as_curl(CURL_LOGGER, url, verb, headers, params, data)
        func = _VERB_TO_METHOD_DICT[verb]
        try:
            resp = func(url, params=params, headers=headers, data=data)
        except requests.exceptions.ConnectionError:
            raise RuntimeError('Could not connect in call of {v} to "{u}"'.format(v=verb, u=url))

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
