#!/usr/bin/env python
from peyotl.api.wrapper import _WSWrapper, APIWrapper
import anyjson
import os
from peyotl import get_logger
_LOG = get_logger(__name__)

class _PhylesystemAPIWrapper(_WSWrapper):
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
    def phylesystem_config(self):
        uri = '{d}/phylesystem_config'.format(d=self.domain)
        return self.json_http_get(uri)
    def external_url(self, study_id):
        uri = '{d}/external_url/{i}'.format(d=self.domain, i=study_id)
        return self.json_http_get(uri)
    def get_study(self, study_id):
        uri = '{d}/v1/study/{i}'.format(d=self.domain, i=study_id)
        return self.json_http_get(uri)

def PhylesystemAPI(domains=None):
    return APIWrapper(domains=domains).phylesystem_api

