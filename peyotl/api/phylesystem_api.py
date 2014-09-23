#!/usr/bin/env python
from peyotl.phylesystem import Phylesystem, PhylesystemProxy
from peyotl.api.wrapper import _WSWrapper, APIWrapper
from peyotl.nexson_syntax import create_content_spec
import anyjson
import urllib
import os
from peyotl import get_logger
_LOG = get_logger(__name__)

_GET_LOCAL, _GET_EXTERNAL, _GET_API = range(3)
_GET_FROM_VALUES = ('local',    # only from local copy of phylesystem
                    'external', # *DEFAULT* from external URLs
                    'api', )    # from the GET calls of the phylesystem-api
# TRANSFORM only relevant when get_from is "api"
_TRANS_CLIENT, _TRANS_SERVER = range(2)
_TRANSFORM_VALUES = ('client', # *DEFAULT* transform to the desired output format on the client side
                     'server', ) # request data transformation take place on the server
# REFRESH is only relevant when get_from is "local"
_REFR_NEVER, _REFR_SESSION, _REFR_ALWAYS = range(3)
_REFRESH_VALUES = ('never',    # *DEFAULT* never call "git pull"
                   'session',  # call "git pull" before the first access
                   'always', ) # do a "git pull" before each data access

class _PhylesystemAPIWrapper(_WSWrapper):
    def __init__(self, domain, **kwargs):
        self._prefix = None
        _WSWrapper.__init__(self, domain)
        self.set_domain(domain)
        self._github_oauth_token = None
        self._get_from = kwargs.setdefault('get_from', 'external').lower()
        self._transform = kwargs.setdefault('transform', 'client').lower()
        self._refresh = kwargs.setdefault('refresh', 'never').lower()
        self._src_code = _GET_FROM_VALUES.index(self._get_from)
        self._trans_code = _TRANSFORM_VALUES.index(self._transform)
        self._refresh_code = _REFRESH_VALUES.index(self._refresh)
        self._repo_nexml2json = None
        self._phylesystem_config = None
        self._phylesystem_obj = None
        self._use_raw = False #TODO should be config dependent...
    def get_domain(self):
        return self._domain
    def set_domain(self, d):
        self._domain = d
        self._prefix = '{d}/phylesystem/v1'.format(d=d)
    domain = property(get_domain, set_domain)
    def get_phylesystem_obj(self):
        if self._phylesystem_obj is None:
            if self._src_code == _GET_LOCAL:
                self._phylesystem_obj = Phylesystem()
            else:
                self._phylesystem_obj = PhylesystemProxy(self.phylesystem_config)
        return self._phylesystem_obj
    phylesystem_obj = property(get_phylesystem_obj)

    def _fetch_phylesystem_config(self):
        if self._src_code == _GET_LOCAL:
            return self.phylesystem_obj.get_configuration_dict()
        else:
            return self._remote_phylesystem_config()
    def get_phylesystem_config(self):
        if self._phylesystem_config is None:
            self._phylesystem_config = self._fetch_phylesystem_config()
        return self._phylesystem_config
    phylesystem_config = property(get_phylesystem_config)

    def get_repo_nexml2json(self):
        if self._repo_nexml2json is None:
            self._repo_nexml2json = self.phylesystem_config['repo_nexml2json']
        return self._repo_nexml2json
    repo_nexml2json = property(get_repo_nexml2json)
    def get_external_url(self, study_id):
        if self._src_code == _GET_API:
            return self._remote_external_url(study_id)['url']
        return self.phylesystem_obj.get_external_url(study_id)
    def get_study_list(self):
        if self._src_code == _GET_API:
            return self._remote_study_list()
        return self.phylesystem_obj.get_study_ids()
    study_list = property(get_study_list)
    def get_push_failure_state(self):
        '''Returns a tuple: the boolean for whether or not pushes succeed, and the
        entire object returned by a call to push_failure on the phylesystem-api.
        This should only be called with wrappers around remote services (RuntimeError
        will be raised if you call this with a local wrapper.
        '''
        if self._src_code == _GET_LOCAL:
            raise RuntimeError('push_failure_state only pertains to work with remote phyleysystem instances')
        r = self._remote_push_failure()
        return r['pushes_succeeding'], r
    push_failure_state = property(get_push_failure_state)
    def get(self, study_id, content=None, schema=None, **kwargs):
        '''Syntactic sugar around to make it easier to get fine-grained access
        to the parts of a file without composing a PhyloSchema object.
        Possible invocations include:
            w.get('pg_10')
            w.get('pg_10', 'trees')
            w.get('pg_10', 'trees', format='nexus')
            w.get('pg_10', tree_id='tree3')
        see:
        '''
        if schema is None:
            schema = create_content_spec(content=content,
                                         repo_nexml2json=self.repo_nexml2json,
                                         **kwargs)
        r = self.get_study(study_id, schema)
        if schema.content == 'study' and schema.format_str == 'nexson':
            return r
        if isinstance(r, dict) and ('data' in r):
            return r['data']
        return r

    def get_study(self, study_id, schema=None):
        if self._src_code == _GET_EXTERNAL:
            url = self.get_external_url(study_id)
            nexson = self.json_http_get(url)
            r = {'data': nexson}
        elif self._src_code == _GET_LOCAL:
            nexson, sha = self.phylesystem_obj.return_study(study_id)
            r = {'data': nexson,
                 'sha': sha}
        else:
            assert self._src_code == _GET_API
            if self._trans_code == _TRANS_SERVER:
                if schema is None:
                    schema = create_content_spec(nexson_version=self.repo_nexml2json)
            r = self._remote_get_study(study_id, schema)
        if (isinstance(r, dict) and 'data' in r) and (self._trans_code == _TRANS_CLIENT) and (schema is not None):
            r['data'] = schema.convert(r['data'])
        return r
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
    def _remote_study_list(self):
        '''Returns a list of strings which are the study IDs'''
        uri = '{}/study_list'.format(self._prefix)
        return self.json_http_get(uri)
    def _remote_push_failure(self):
        '''Returns a list of strings which are the study IDs'''
        uri = '{}/push_failure'.format(self._prefix)
        return self.json_http_get(uri)
    def unmerged_branches(self):
        uri = '{}/unmerged_branches'.format(self._prefix)
        return self.json_http_get(uri)
    def post_study(self,
                   nexson,
                   study_id=None,
                   commit_msg=None):
        assert nexson is not None
        if study_id is None:
            uri = '{d}/study'.format(d=self._prefix)
        else:
            uri = '{d}/study/{i}'.format(d=self._prefix, i=study_id)
        params = {'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_post(uri,
                                   params=params,
                                   data=anyjson.dumps({'nexson': nexson}))
    def put_study(self,
                  study_id,
                  nexson,
                  starting_commit_sha,
                  commit_msg=None):
        assert nexson is not None
        uri = '{d}/study/{i}'.format(d=self._prefix, i=study_id)
        params = {'starting_commit_SHA':starting_commit_sha,
                  'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_put(uri,
                                  params=params,
                                  data=anyjson.dumps({'nexson': nexson}))
    def _remote_phylesystem_config(self):
        uri = '{d}/phylesystem_config'.format(d=self._prefix)
        return self.json_http_get(uri)
    def _remote_external_url(self, study_id):
        uri = '{d}/external_url/{i}'.format(d=self._prefix, i=study_id)
        return self.json_http_get(uri)
    def url_for_api_get_study(self, study_id, schema):
        u, d = schema.phylesystem_api_url(self._prefix, study_id)
        if d:
            return '{u}?{d}'.format(u=u, d=urllib.urlencode(d))
        return u

    def _remote_get_study(self, study_id, schema):
        data = {}
        expect_json = True
        if self._trans_code == _TRANS_SERVER:
            uri, params = schema.phylesystem_api_url(self._prefix, study_id)
            data.update(params)
            expect_json = schema.is_json()
        else:
            uri = '{d}/study/{i}'.format(d=self._prefix, i=study_id)
            data['output_nexml2json'] = 'native'
        if not data:
            data = None
        return self.json_http_get(uri, params=data, text=not expect_json)

def PhylesystemAPI(domains=None, **kwargs):
    return APIWrapper(domains=domains, **kwargs).wrap_phylesystem_api(**kwargs)

