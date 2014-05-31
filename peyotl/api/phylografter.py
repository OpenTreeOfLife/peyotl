#!/usr/bin/env python
from cStringIO import StringIO
from peyotl.api.wrapper import _WSWrapper, APIWrapper, GZIP_REQUEST_HEADERS
from peyotl.nexson_syntax import write_as_json
import datetime
import anyjson
import requests
import gzip
from peyotl import get_logger
_LOG = get_logger(__name__)


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
        uri = self.domain + '/study/modified_list.json/url'
        args = {'from': since_date}
        r = self.json_http_get(uri, params=args)
        if list_only:
            return r['studies']
        return r

    def fetch_nexson(self, study_id, output_filepath=None, store_raw=False):
        '''Calls export_gzipNexSON URL and unzips response.
        Raises HTTP error, gzip module error, or RuntimeError
        '''
        if study_id.startswith('pg_'):
            study_id = study_id[3:] #strip pg_ prefix
        uri = self.domain + '/study/export_gzipNexSON.json/' + study_id
        _LOG.debug('Downloading %s using "%s"\n', study_id, uri)
        resp = requests.get(uri,
                            headers=GZIP_REQUEST_HEADERS,
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
                return anyjson.loads(results)
            else:
                if store_raw:
                    write_to_filepath(results, output_filepath)
                else:
                    write_as_json(anyjson.loads(results), output_filepath)
                return True
        raise RuntimeError('gzipped response from phylografter export_gzipNexSON.json, but not a string is:', results)
    # alias fetch_nexson
    fetch_study = fetch_nexson

def Phylografter(domains=None):
    return APIWrapper(domains=domains).phylografter
