#!/usr/bin/env python
from peyotl.collections.collections_umbrella import TreeCollectionStore, TreeCollectionStoreProxy
from peyotl.api.wrapper import _WSWrapper, APIWrapper
from peyotl.collections import COLLECTION_ID_PATTERN
from peyotl.utility import get_logger
import anyjson
import urllib
import os
_LOG = get_logger(__name__)

_GET_LOCAL, _GET_EXTERNAL, _GET_API = range(3)
_GET_FROM_VALUES = ('local',    # only from local copy of collections
                    'external', # *DEFAULT* from external URLs
                    'api', )    # from the GET calls of the collections-api

### TRANSFORM only relevant when get_from is "api"
##_TRANS_CLIENT, _TRANS_SERVER = range(2)
##_TRANSFORM_VALUES = ('client', # *DEFAULT* transform to the desired output format on the client side
##                     'server', ) # request data transformation take place on the server

# REFRESH is only relevant when get_from is "local"
_REFR_NEVER, _REFR_SESSION, _REFR_ALWAYS = range(3)
_REFRESH_VALUES = ('never',    # *DEFAULT* never call "git pull"
                   'session',  # call "git pull" before the first access
                   'always', ) # do a "git pull" before each data access

class _TreeCollectionsAPIWrapper(_WSWrapper):
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
        self._store_config = None
        self._docstore_obj = None
        self._use_raw = False
    @property
    def domain(self):
        return self._domain
    @domain.setter
    def domain(self, d):#pylint: disable=W0221
        self._domain = d
        self._prefix = '{d}/v2'.format(d=d)
    @property
    def docstore_obj(self):
        if self._docstore_obj is None:
            if self._src_code == _GET_LOCAL:
                self._docstore_obj = TreeCollectionStore()
            else:
                self._docstore_obj = TreeCollectionStoreProxy(self.store_config)
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
    def get_external_url(self, collection_id):
        if self._src_code == _GET_API:
            return self._remote_external_url(collection_id)['url']
        return self.docstore_obj.get_external_url(collection_id)
    @property
    def collection_list(self):
        if self._src_code == _GET_API:
            return self._remote_collection_list()
        return self.docstore_obj.get_collection_ids()
    @property
    def push_failure_state(self):
        '''Returns a tuple: the boolean for whether or not pushes succeed, and the
        entire object returned by a call to push_failure on the phylesystem-api.
        This should only be called with wrappers around remote services (RuntimeError
        will be raised if you call this with a local wrapper.
        '''
        if self._src_code == _GET_LOCAL:
            raise RuntimeError('push_failure_state only pertains to work with remote phyleysystem instances')
        r = self._remote_push_failure()
        return r['pushes_succeeding'], r
    def get(self, collection_id, content=None, schema=None, **kwargs):
        '''Syntactic sugar around to make it easier to get fine-grained access
        to the parts of a file without composing a PhyloSchema object.
        Possible invocations include:
            w.get('pg_10')
            w.get('pg_10', 'trees')
            w.get('pg_10', 'trees', format='nexus')
            w.get('pg_10', tree_id='tree3')
        see:
        '''
        assert COLLECTION_ID_PATTERN.match(collection_id)
        r = self.get_collection(collection_id, schema)
        #if schema.content == 'study' and schema.format_str == 'nexson':
        #    return r
        if isinstance(r, dict) and ('data' in r):
            return r['data']
        return r

    def get_collection(self, collection_id, schema=None):
        if self._src_code == _GET_EXTERNAL:
            url = self.get_external_url(collection_id)
            nexson = self.json_http_get(url)
            r = {'data': nexson}
        elif self._src_code == _GET_LOCAL:
            nexson, sha = self.docstore_obj.return_doc(collection_id) #pylint: disable=W0632
            r = {'data': nexson,
                 'sha': sha}
        else:
            assert self._src_code == _GET_API
            r = self._remote_get_collection(collection_id, schema)
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
    def _remote_collection_list(self):
        '''Returns a list of strings which are the collection IDs'''
        uri = '{}/collections/collection_list'.format(self._prefix)
        return self.json_http_get(uri)
    def _remote_push_failure(self):
        '''Returns a list of strings which are the collection IDs'''
        uri = '{}/collections/push_failure'.format(self._prefix)
        return self.json_http_get(uri)
    def unmerged_branches(self):
        uri = '{}/collections/unmerged_branches'.format(self._prefix)
        return self.json_http_get(uri)
    def post_collection(self,
                        json,
                        collection_id=None,
                        commit_msg=None):
        assert json is not None
        if collection_id is None:
            uri = '{d}/collection'.format(d=self._prefix)
        else:
            uri = '{d}/collection/{i}'.format(d=self._prefix, i=collection_id)
        params = {'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_post(uri,
                                   params=params,
                                   data=anyjson.dumps({'json': json}))
    def put_collection(self,
                       collection_id,
                       json,
                       starting_commit_sha,
                       commit_msg=None):
        assert json is not None
        uri = '{d}/collection/{i}'.format(d=self._prefix, i=collection_id)
        params = {'starting_commit_SHA':starting_commit_sha,
                  'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_put(uri,
                                  params=params,
                                  data=anyjson.dumps({'json': json}))
    def delete_collection(self,
                          collection_id,
                          starting_commit_sha,
                          commit_msg=None):
        uri = '{d}/collection/{i}'.format(d=self._prefix, i=collection_id)
        params = {'starting_commit_SHA':starting_commit_sha,
                  'auth_token': self.auth_token}
        if commit_msg:
            params['commit_msg'] = commit_msg
        return self.json_http_delete(uri,
                                     params=params)
    def _remote_store_config(self):
        uri = '{d}/collections/store_config'.format(d=self._prefix)
        return self.json_http_get(uri)
    def _remote_external_url(self, collection_id):
        uri = '{d}/collections/external_url/{i}'.format(d=self._prefix, i=collection_id)
        return self.json_http_get(uri)
    def url_for_api_get_collection(self, collection_id, schema):
        u, d = schema.phylesystem_api_url(self._prefix, collection_id)
        if d:
            return '{u}?{d}'.format(u=u, d=urllib.urlencode(d))
        return u

    def _remote_get_collection(self, collection_id, schema):
        uri = '{d}/collection/{i}'.format(d=self._prefix, i=collection_id)
        return self.json_http_get(uri)  # , params=None, text=False)

def TreeCollectionsAPI(domains=None, **kwargs):
    return APIWrapper(domains=domains, **kwargs).wrap_collections_api(**kwargs)

