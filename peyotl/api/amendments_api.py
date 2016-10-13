#!/usr/bin/env python
from peyotl.amendments.amendments_umbrella import TaxonomicAmendmentStore, TaxonomicAmendmentStoreProxy
from peyotl.api.wrapper import _WSWrapper, APIWrapper
from peyotl.amendments import AMENDMENT_ID_PATTERN
from peyotl.utility import get_logger
import anyjson
import os

_LOG = get_logger(__name__)

_GET_LOCAL, _GET_EXTERNAL, _GET_API = range(3)
_GET_FROM_VALUES = ('local',  # only from local copy of amendments
                    'external',  # *DEFAULT* from external URLs
                    'api',)  # from the GET calls of the amendments-api

# TRANSFORM only relevant when get_from is "api"
#_TRANS_CLIENT, _TRANS_SERVER = range(2)
#_TRANSFORM_VALUES = ('client', # *DEFAULT* transform to the desired output format on the client side
#                     'server', ) # request data transformation take place on the server

# REFRESH is only relevant when get_from is "local"
_REFR_NEVER, _REFR_SESSION, _REFR_ALWAYS = range(3)
_REFRESH_VALUES = ('never',  # *DEFAULT* never call "git pull"
                   'session',  # call "git pull" before the first access
                   'always',)  # do a "git pull" before each data access


class _TaxonomicAmendmentsAPIWrapper(_WSWrapper):
    def __init__(self, domain, **kwargs):
        self._prefix = None
        _WSWrapper.__init__(self, domain, **kwargs)
        self.domain = domain
        self._github_oauth_token = None
        self._get_from = kwargs.setdefault('get_from', 'external').lower()
        self._transform = kwargs.setdefault('transform', 'client').lower()
        self._refresh = kwargs.setdefault('refresh', 'never').lower()
        self._src_code = _GET_FROM_VALUES.index(self._get_from)
        self._refresh_code = _REFRESH_VALUES.index(self._refresh)
        self._assumed_doc_version = None
        self._locals_repo_dict = kwargs.get('locals_repos_dict')  # repos_dict arg to Phylesystem() if get_from is local
        self._store_config = None
        self._docstore_obj = None
        self._use_raw = False

    @property
    def domain(self):
        return self._domain

    @domain.setter
    def domain(self, d):  # pylint: disable=W0221
        self._domain = d
        self._prefix = '{d}/v3'.format(d=d)

    @property
    def docstore_obj(self):
        if self._docstore_obj is None:
            if self._src_code == _GET_LOCAL:
                self._docstore_obj = TaxonomicAmendmentStore(repos_dict=self._locals_repo_dict)
            else:
                self._docstore_obj = TaxonomicAmendmentStoreProxy(self.store_config)
        return self._docstore_obj

    def _fetch_store_config(self):
        if self._src_code == _GET_LOCAL:
            return self.docstore_obj.get_configuration_dict()
        else:
            return self._remote_store_config()

    @property
    def store_config(self):
        if self._store_config is None:
            self._store_config = self._fetch_store_config()
        return self._store_config

    @property
    def assumed_doc_version(self):
        if self._assumed_doc_version is None:
            self._assumed_doc_version = self.store_config.get('assumed_doc_version')
            if self._assumed_doc_version is None:
                # TODO: remove this fall-back to legacy configuration once deployed phylesystems are up to date
                self._assumed_doc_version = self.store_config.get('repo_nexml2json')
        return self._assumed_doc_version

    def get_external_url(self, amendment_id):
        if self._src_code == _GET_API:
            return self._remote_external_url(amendment_id)['url']
        return self.docstore_obj.get_external_url(amendment_id)

    @property
    def amendment_list(self):
        if self._src_code == _GET_API:
            return self._remote_amendment_list()
        return self.docstore_obj.get_amendment_ids()

    @property
    def push_failure_state(self):
        """Returns a tuple: the boolean for whether or not pushes succeed, and the
        entire object returned by a call to push_failure on the phylesystem-api.
        This should only be called with wrappers around remote services (RuntimeError
        will be raised if you call this with a local wrapper.
        """
        if self._src_code == _GET_LOCAL:
            raise RuntimeError('push_failure_state only pertains to work with remote phyleysystem instances')
        r = self._remote_push_failure()
        return r['pushes_succeeding'], r

    def get(self, amendment_id, content=None, **kwargs):
        """Syntactic sugar around to make it easier to get fine-grained access
        to the parts of a file without composing a PhyloSchema object.
        Possible invocations include:
            w.get('pg_10')
            w.get('pg_10', 'trees')
            w.get('pg_10', 'trees', format='nexus')
            w.get('pg_10', tree_id='tree3')
        see:
        """
        assert AMENDMENT_ID_PATTERN.match(amendment_id)
        r = self.get_amendment(amendment_id)
        if isinstance(r, dict) and ('data' in r):
            return r['data']
        return r

    def get_amendment(self, amendment_id):
        if self._src_code == _GET_EXTERNAL:
            url = self.get_external_url(amendment_id)
            json = self.json_http_get(url)
            r = {'data': json}
        elif self._src_code == _GET_LOCAL:
            json, sha = self.docstore_obj.return_doc(amendment_id)  # pylint: disable=W0632
            r = {'data': json,
                 'sha': sha}
        else:
            assert self._src_code == _GET_API
            r = self._remote_get_amendment(amendment_id)
        return r

    @property
    def auth_token(self):
        if self._github_oauth_token is None:
            auth_token = os.environ.get('GITHUB_OAUTH_TOKEN')
            if auth_token is None:
                raise RuntimeError('''To use the write methods of the Open Tree of Life's document stores
you must supply a GitHub OAuth Token. Peyotl uses the GITHUB_OAUTH_TOKEN environmental
variable to obtain this token. If you need to obtain your key, see the instructions at:
    https://github.com/OpenTreeOfLife/api.opentreeoflife.org/tree/master/docs#getting-a-github-oauth-token
''')
            self._github_oauth_token = auth_token
        _LOG.debug('auth_token first test: {}'.format(self._github_oauth_token))
        return self._github_oauth_token

    def _remote_amendment_list(self):
        """Returns a list of strings which are the amendment IDs"""
        uri = '{}/amendments/amendment_list'.format(self._prefix)
        return self.json_http_get(uri)

    def _remote_push_failure(self):
        """Returns a list of strings which are the amendment IDs"""
        uri = '{}/amendments/push_failure'.format(self._prefix)
        return self.json_http_get(uri)

    def unmerged_branches(self):
        uri = '{}/amendments/unmerged_branches'.format(self._prefix)
        return self.json_http_get(uri)

    def post_amendment(self,
                       json,
                       commit_msg=None):
        assert json is not None
        uri = '{d}/amendment'.format(d=self._prefix)
        params = {'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_post(uri,
                                   params=params,
                                   data=anyjson.dumps({'json': json}))

    def put_amendment(self,
                      amendment_id,
                      json,
                      starting_commit_sha,
                      commit_msg=None):
        assert json is not None
        uri = '{d}/amendment/{i}'.format(d=self._prefix, i=amendment_id)
        params = {'starting_commit_SHA': starting_commit_sha,
                  'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_put(uri,
                                  params=params,
                                  data=anyjson.dumps({'json': json}))

    def delete_amendment(self,
                         amendment_id,
                         starting_commit_sha,
                         commit_msg=None):
        uri = '{d}/amendment/{i}'.format(d=self._prefix, i=amendment_id)
        params = {'starting_commit_SHA': starting_commit_sha,
                  'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_delete(uri,
                                     params=params)

    def _remote_store_config(self):
        uri = '{d}/amendments/store_config'.format(d=self._prefix)
        return self.json_http_get(uri)

    def _remote_external_url(self, amendment_id):
        uri = '{d}/amendments/external_url/{i}'.format(d=self._prefix, i=amendment_id)
        return self.json_http_get(uri)

    def _remote_get_amendment(self, amendment_id):
        uri = '{d}/amendment/{i}'.format(d=self._prefix, i=amendment_id)
        return self.json_http_get(uri)  # , params=None, text=False)


# noinspection PyPep8Naming
def TaxonomicAmendmentsAPI(domains=None, **kwargs):
    return APIWrapper(domains=domains, **kwargs).wrap_amendments_api(**kwargs)
