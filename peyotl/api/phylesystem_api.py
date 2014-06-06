#!/usr/bin/env python
from peyotl.api.wrapper import _WSWrapper, APIWrapper
import anyjson
import os
from peyotl import get_logger
_LOG = get_logger(__name__)

_GET_LOCAL, _GET_EXTERNAL, _GET_API = range(3)
_GET_FROM_VALUES = ('local',    # only from local copy of phylesystem
                    'external', # *DEFAULT* from external URLs
                    'api',      # from the GET calls of the phylesystem-api
                    )
# TRANSFORM only relevant when get_from is "api"
_TRANS_CLIENT, _TRANS_SERVER = range(2)
_TRANSFORM_VALUES = ('client', # *DEFAULT* transform to the desired output format on the client side
                     'server', # request data transformation take place on the server
                     )
# REFRESH is only relevant when get_from is "local"
_REFR_NEVER, _REFR_SESSION, _REFR_ALWAYS = range(3)
_REFRESH_VALUES = ('never',    # *DEFAULT* never call "git pull"
                   'session',  # call "git pull" before the first access
                   'always',   # do a "git pull" before each data access
                   )

class _PhylesystemAPIWrapper(_WSWrapper):
    def __init__(self, domain, **kwargs):
        _WSWrapper.__init__(self, domain)
        self._github_oauth_token = None
        self._get_from = kwargs.setdefault('get_from', 'external').lower()
        self._transform = kwargs.setdefault('transform', 'client').lower()
        self._refresh = kwargs.setdefault('refresh', 'never').lower()
        self._src_code = _GET_FROM_VALUES.index(self._get_from)
        self._trans_code = _TRANSFORM_VALUES.index(self._transform)
        self._refresh_code = _REFRESH_VALUES.index(self._refresh)
    def get_study(self, study_id, schema=None):
        if self._src_code == _GET_EXTERNAL:
            url = self.get_external_url(study_id)
            return self.json_http_get(url)
        elif self._src_code == _GET_LOCAL:
            nexson, sha = self.phylesystem.return_study(study_id)
            return nexson
        else:
          assert self._src_code == _GET_API
          return self._remote_get_study(study_id, schema)
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
        uri = '{}/study_list'.format(self.domain)
        return self.json_http_get(uri)
    def unmerged_branches(self):
        uri = '{}/unmerged_branches'.format(self.domain)
        return self.json_http_get(uri)
    def post_study(self,
                   nexson,
                   study_id=None,
                   commit_msg=None):
        assert nexson is not None
        if study_id is None:
            uri = '{d}/v1/study'.format(d=self.domain)
        else:
            uri = '{d}/v1/study/{i}'.format(d=self.domain, i=study_id)
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
        uri = '{d}/v1/study/{i}'.format(d=self.domain, i=study_id)
        params = {'starting_commit_SHA':starting_commit_sha,
                  'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_put(uri,
                         params=params,
                         data=anyjson.dumps({'nexson': nexson}))
    def _remote_phylesystem_config(self):
        uri = '{d}/phylesystem_config'.format(d=self.domain)
        return self.json_http_get(uri)
    def _remote_external_url(self, study_id):
        uri = '{d}/external_url/{i}'.format(d=self.domain, i=study_id)
        return self.json_http_get(uri)
    def _remote_get_study(self, study_id, schema=None):
        uri = '{d}/v1/study/{i}'.format(d=self.domain, i=study_id)
        data = {}
        if (schema is not None) and (self._trans_code == _TRANS_CLIENT):
            suff = schema.create_phylesystem_api_suffix()
            if suff:
                uri = '{u}/{s}'.format(u=uri, s=suff)
        else:
            pass # data['output_nexml2json'] = 'native'
        if not data:
            data = None
        return self.json_http_get(uri, params=data)

def PhylesystemAPI(domains=None, **kwargs):
    return APIWrapper(domains=domains).wrap_phylesystem_api(**kwargs)

