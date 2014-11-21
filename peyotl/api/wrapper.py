#!/usr/bin/env python
from peyotl.utility.str_util import UNICODE, is_str_type
from peyotl.utility import get_config_object, get_logger
import requests
import warnings
import codecs
import anyjson
import os
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
    if not is_str_type(s):
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
            if is_str_type(data):
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
        self._config = get_config_object(None, **kwargs)
        self._oti = kwargs.get('oti')
        self._phylografter = 'http://www.reelab.net/phylografter'
        self._phylesystem_api = kwargs.get('phylesystem')
        self._taxomachine = kwargs.get('taxomachine')
        self._treemachine = kwargs.get('treemachine')
    @property
    def oti(self):
        if self._oti is None:
            self._oti = self._config.get_config_setting('apis',
                                                        'oti',
                                                        'http://api.opentreeoflife.org')
        return self._oti
    @property
    def phylesystem_api(self):
        if self._phylesystem_api is None:
            self._phylesystem_api = self._config.get_config_setting('apis',
                                                                    'phylesystem_api',
                                                                    'http://api.opentreeoflife.org')
        return self._phylesystem_api
    @property
    def phylografter(self):
        return self._phylografter
    @property
    def taxomachine(self):
        if self._taxomachine is None:
            self._taxomachine = self._config.get_config_setting('apis',
                                                                'taxomachine',
                                                                'http://api.opentreeoflife.org')
        return self._taxomachine
    @property
    def treemachine(self):
        if self._treemachine is None:
            self._treemachine = self._config.get_config_setting('apis',
                                                                'treemachine',
                                                                'http://api.opentreeoflife.org')
        return self._treemachine

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
        self._config = get_config_object(None, **kwargs)
        if phylesystem_api_kwargs is None:
            self._phylesystem_api_kwargs = {}
        else:
            self._phylesystem_api_kwargs = dict(phylesystem_api_kwargs)
    @property
    def oti(self):
        from peyotl.api.oti import _OTIWrapper #pylint: disable=R0401
        if self._oti is None:
            self._oti = _OTIWrapper(self.domains.oti, config=self._config)
        return self._oti
    def wrap_phylesystem_api(self, **kwargs):
        from peyotl.api.phylesystem_api import _PhylesystemAPIWrapper
        cfrom = self._config.get_config_setting('apis',
                                                'phylesystem_get_from',
                                                self._phylesystem_api_kwargs.get('get_from', 'external'))
        ctrans = self._config.get_config_setting('apis',
                                                 'phylesystem_transform',
                                                 self._phylesystem_api_kwargs.get('transform', 'client'))
        crefresh = self._config.get_config_setting('apis',
                                                   'phylesystem_refresh',
                                                   self._phylesystem_api_kwargs.get('refresh', 'never'))
        if cfrom:
            kwargs.setdefault('get_from', cfrom)
        if ctrans:
            kwargs.setdefault('transform', ctrans)
        if crefresh:
            kwargs.setdefault('refresh', crefresh)
        kwargs['config'] = self._config
        self._phylesystem_api = _PhylesystemAPIWrapper(self.domains.phylesystem_api, **kwargs)
        return self._phylesystem_api
    @property
    def phylesystem_api(self):
        if self._phylesystem_api is None:
            self.wrap_phylesystem_api()
        return self._phylesystem_api
    @property
    def phylografter(self):
        from peyotl.api.phylografter import _PhylografterWrapper
        if self._phylografter is None:
            self._phylografter = _PhylografterWrapper(self.domains.phylografter, config=self._config)
        return self._phylografter
    @property
    def taxomachine(self):
        from peyotl.api.taxomachine import _TaxomachineAPIWrapper
        if self._taxomachine is None:
            self._taxomachine = _TaxomachineAPIWrapper(self.domains.taxomachine, config=self._config)
        return self._taxomachine
    @property
    def treemachine(self):
        from peyotl.api.treemachine import _TreemachineAPIWrapper
        if self._treemachine is None:
            self._treemachine = _TreemachineAPIWrapper(self.domains.treemachine, config=self._config)
        return self._treemachine
    @property
    def tree_of_life(self):
        if self._tree_of_life_wrapper is None:
            self._tree_of_life_wrapper = _TreeOfLifeServicesWrapper(self.treemachine, config=self._config)
        return self._tree_of_life_wrapper
    @property
    def graph(self):
        if self._graph_wrapper is None:
            self._graph_wrapper = _GraphOfLifeServicesWrapper(self.treemachine, config=self._config)
        return self._graph_wrapper
    @property
    def study(self):
        if self._study_wrapper is None:
            self._study_wrapper = _StudyServicesWrapper(self.phylesystem_api, config=self._config)
        return self._study_wrapper
    @property
    def tnrs(self):
        if self._tnrs_wrapper is None:
            self._tnrs_wrapper = _TNRSServicesWrapper(self.taxomachine, config=self._config)
        return self._tnrs_wrapper
    @property
    def taxonomy(self):
        if self._taxonomy_wrapper is None:
            self._taxonomy_wrapper = _TaxonomyServicesWrapper(self.taxomachine, config=self._config)
        return self._taxonomy_wrapper
    @property
    def studies(self):
        if self._studies_wrapper is None:
            self._studies_wrapper = _StudiesServicesWrapper(self.oti, config=self._config)
        return self._studies_wrapper

class _StudiesServicesWrapper(object):
    def __init__(self, oti_wrapper, **kwargs):
        self.oti = oti_wrapper
    def find_studies(self, *valist, **kwargs):
        return self.oti.find_studies(*valist, **kwargs)
    def find_trees(self, *valist, **kwargs):
        return self.oti.find_trees(*valist, **kwargs)
    def properties(self):
        return self.oti.search_terms

class _TaxonomyServicesWrapper(object):
    def __init__(self, taxomachine_wrapper, **kwargs):
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
    def __init__(self, taxomachine_wrapper, **kwargs):
        self.taxomachine = taxomachine_wrapper
    def match_names(self, *valist, **kwargs):
        return self.taxomachine.TNRS(*valist, **kwargs)
    def autocomplete_name(self, *valist, **kwargs):
        return self.taxomachine.autocomplete(*valist, **kwargs)
    def contexts(self, *valist, **kwargs):
        return self.taxomachine.contexts(*valist, **kwargs)
    def infer_context(self, *valist, **kwargs):
        return self.taxomachine.infer_context(*valist, **kwargs)

class _StudyServicesWrapper(object):
    def __init__(self, phylesystem_api, **kwargs):
        self.phylesytem_wrapper = phylesystem_api
    def get(self, *valist, **kwargs):
        return self.phylesytem_wrapper.get(*valist, **kwargs)

class _GraphOfLifeServicesWrapper(object):
    def __init__(self, treemachine_wrapper, **kwargs):
        self.treemachine = treemachine_wrapper
    def info(self):
        return self.treemachine.graph_info
    about = info
    def source_tree(self, *valist, **kwargs):
        return self.treemachine.get_source_tree(*valist, **kwargs)
    def node_info(self, *valist, **kwargs):
        return self.treemachine.node_info(*valist, **kwargs)

class _TreeOfLifeServicesWrapper(object):
    def __init__(self, treemachine_wrapper, **kwargs):
        self.treemachine = treemachine_wrapper
    def info(self):
        return self.treemachine.synthetic_tree_info
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
    dk = list(d.keys())
    dk.sort()
    sd = UNICODE(d)
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
    elif is_str_type(data):
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
    def __init__(self, domain, **kwargs):
        self._domain = domain
    #pylint: disable=W0102
    def json_http_get(self, url, headers=_JSON_HEADERS, params=None, text=False): #pylint: disable=W0102
        # See https://github.com/kennethreitz/requests/issues/1882 for discussion of warning suppression
        with warnings.catch_warnings():
            try:
                warnings.simplefilter("ignore", ResourceWarning) #pylint: disable=E0602
            except NameError:
                pass # on py2.7 we don't have ResourceWarning, but we don't need to filter...
            return self._do_http(url, 'GET', headers=headers, params=params, data=None, text=text)
    def json_http_put(self, url, headers=_JSON_HEADERS, params=None, data=None, text=False): #pylint: disable=W0102
        # See https://github.com/kennethreitz/requests/issues/1882 for discussion of warning suppression
        with warnings.catch_warnings():
            try:
                warnings.simplefilter("ignore", ResourceWarning) #pylint: disable=E0602
            except NameError:
                pass # on py2.7 we don't have ResourceWarning, but we don't need to filter...
            return self._do_http(url, 'PUT', headers=headers, params=params, data=data, text=text)
    def json_http_post(self, url, headers=_JSON_HEADERS, params=None, data=None, text=False): #pylint: disable=W0102
        # See https://github.com/kennethreitz/requests/issues/1882 for discussion of warning suppression
        with warnings.catch_warnings():
            try:
                warnings.simplefilter("ignore", ResourceWarning) #pylint: disable=E0602
            except NameError:
                pass # on py2.7 we don't have ResourceWarning, but we don't need to filter...
            return self._do_http(url, 'POST', headers=headers, params=params, data=data, text=text)
    def json_http_post_raise(self, url, headers=_JSON_HEADERS, params=None, data=None, text=False): #pylint: disable=W0102
        r = self.json_http_post(url, headers=headers, params=params, data=data, text=text)
        if 'error' in r:
            raise ValueError(r['error'])
        return r
    def _do_http(self, url, verb, headers, params, data, text=False): #pylint: disable=R0201
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
    @property
    def domain(self):
        return self._domain
    @domain.setter
    def domain(self, d):
        self._domain = d

