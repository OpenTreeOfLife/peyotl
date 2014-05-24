#!/usr/bin/env python
from peyotl.utility.io import open_for_group_write
import codecs
import json
import stat
import time
import os
from peyotl import get_logger
_LOG = get_logger(__name__)

def get_processing_paths_from_prefix(pref,
                                     nexson_dir='.',
                                     nexson_state_db=None):
    d = {'nexson': os.path.abspath(os.path.join(nexson_dir, 'study', pref + '.json')),
         'nexson_state_db': nexson_state_db,
         'study': pref,
         }
    assert nexson_state_db is not None
    return d



def get_previous_list_of_dirty_nexsons(dir_dict):
    '''Returns the previous list of studies to be fetch and dict that contains that list and timestamps.
    The dict will be populated from the filepath `dir_dict['nexson_state_db']` if that entry is not 
    found then a default dict of no studies and old timestamps will be returned.
    '''
    filename = dir_dict['nexson_state_db']
    if os.path.exists(filename):
        old = json.load(codecs.open(filename, 'rU', encoding='utf-8'))
    else:
        old = {'from': '2010-01-01T00:00:00',
               'to': '2010-01-01T00:00:00',
               'studies': []
        }
    return old['studies'], old

def store_state_JSON(s, fp):
    tmpfilename = fp + '.tmpfile'
    td = open_for_group_write(tmpfilename, 'w')
    try:
        json.dump(s, td, sort_keys=True, indent=0)
    finally:
        td.close()
    os.rename(tmpfilename, fp) #atomic on POSIX

class PhylografterNexsonDocStoreSync(object):
    def __init__(self,
                 cfg_file_paths,
                 lock_policy=None,
                 api_wrapper=None,
                 sleep_between_downloads=None):
        '''Configures an object for controlling the 
        synchronization between phylografter and the NexSON Document Store API.

        `cfg_file_paths` should be a dict with:
            'nexson_dir': directory that will be the parent of the nexson files
             'nexson_state_db': a JSON file to hold the state of the phylografter <-> API interaction
        `to_download` can be a list of study IDs (if the state is not to be preserved). If this call
            uses the history in `cfg_file_paths['nexson_state_db']` then this should be None.
        `lock_policy` can usually be None, it specifies how the nexson_state_db is to be locked for thread safety
        `api_wrapper` will be the default APIWrapper() if None
        `sleep_between_downloads` is the number of seconds to sleep between calls (to avoid stressing phylografter.)

        env vars:
            SLEEP_BETWEEN_DOWNLOADS_TIME, SLEEP_FOR_LOCK_TIME, and MAX_NUM_SLEEP_IN_WAITING_FOR_LOCK are checked
            if lock_policy and sleep_between_downloads
        '''
        self._cfg = cfg_file_paths
        if api_wrapper is None:
            from peyotl.api import APIWrapper
            api_wrapper = APIWrapper()
        self.phylografter = api_wrapper.phylografter
        self.doc_store = api_wrapper.doc_store
        if sleep_between_downloads is None:
            sleep_between_downloads = float(os.environ.get('SLEEP_BETWEEN_DOWNLOADS_TIME', 0.5))
        self.sleep_between_downloads = sleep_between_downloads
        if lock_policy is None:
            from peyotl.utility.simple_file_lock import LockPolicy
            lock_policy = LockPolicy(sleep_time=float(os.environ.get('SLEEP_FOR_LOCK_TIME', 0.05)),
                                     max_num_sleep=int(os.environ.get('MAX_NUM_SLEEP_IN_WAITING_FOR_LOCK', 100)))
        self.lock_policy = lock_policy
        self.log = {}
    def _reset_log(self):
        self.log = {
            'pull_from_phylografter_failed': [],
            'PUT_to_docstore_failed': [],
            'POST_to_docstore_failed': [],
        }

    def _failed_study(self, study, err_key):
        self.log.setdefault(err_key, []).append(study)
        _LOG.debug('{} for study {}'.format(err_key, str(study)))

    def _add_study_to_download_list(self, study, paths):
        if self.downloaded_db is not None:
            self.download_db['studies'].add(int(study))
            # act as if the study was not downloaded, so that when we try
            #   again we won't skip this study
            store_state_JSON(self.download_db, paths['nexson_state_db'])

    def run(self, to_download=None):
        '''Returns the # of studies updated from phylografter to the "NexSON API"

        `to_download` can be a list of study IDs (if the state is not to be preserved). If this call
            uses the history in `cfg_file_paths['nexson_state_db']` then this should be None.
        '''
        self._reset_log()
        if to_download is None:
            to_download, self.download_db = self.get_list_of_phylografter_dirty_nexsons()
            if not to_download:
                return 0
        else:
            self.downloaded_db = None
        num_downloaded = len(to_download)
        studies_with_final_sha = set()
        unmerged_study_to_sha = {}
        last_merged_sha = None
        doc_store_api = self.doc_store
        phylografter = self.phylografter
        first_download = True
        try:
            while len(to_download) > 0:
                if not first_download:
                    raise NotImplementedError('looping over studies')
                    time.sleep(self.sleep_between_downloads)
                first_download = False
                n = to_download.pop(0)
                study = str(n)
                paths = get_processing_paths_from_prefix(study, **self._cfg)
                nexson = self.download_nexson_from_phylografter(paths, phylografter)
                if nexson is None:
                    self._failed_study(study, 'pull_from_phylografter_failed')
                    continue
                try:
                    namespaced_id = 'pg_{s:d}'.format(s=study)
                    parent_sha = self.find_parent_sha_for_phylografter_nexson(study, nexson)
                    if study in self.doc_store_studies:
                        ds_method = doc_store_api.put_study
                        ds_verb = 'PUT'
                    else:
                        ds_method = doc_store_api.post_study
                        ds_verb = 'POST'
                    put_response = ds_method(study_id=namespaced_id,
                                             nexson=nexson,
                                             starting_commit_sha=parent_sha)
                    if put_response['error'] != '0':
                        self._failed_study(study, '{}_to_docstore_failed'.format(ds_verb))
                        self._add_study_to_download_list(study, paths)
                        continue
                except:
                    self._add_study_to_download_list(study, paths)
                    raise
                else:
                    if put_response['merge_needed']:
                        unmerged_study_to_sha[study] = put_response['sha']
                    else:
                        studies_with_final_sha.add(study)
                        last_merged_sha = put_response['sha']
        finally:
            self.record_sha_for_study(studies_with_final_sha,
                                      unmerged_study_to_sha,
                                      last_merged_sha)
        return num_downloaded

    def get_list_of_phylografter_dirty_nexsons(self):
        '''Returns a pair: the list of studies that need to be fetched from phylografter
        and a dict that can be serialized to disk in .sync_status.json to cache the details
        of the last call to phylografter's study/modified_list service.

        If PHYLOGRAFTER_DOMAIN_PREF is in the env, it will provide the domain the default
            is the main phylografter site.
        '''
        dir_dict, phylografter = self._cfg, self.phylografter
        filename = dir_dict['nexson_state_db']
        slist, old = get_previous_list_of_dirty_nexsons(dir_dict)
        new_resp = phylografter.get_modified_list(old['to'])
        ss = set(new_resp['studies'] + old['studies'])
        sl = list(ss)
        sl.sort()
        new_resp['studies'] = sl
        new_resp['from'] = old['from']
        store_state_JSON(new_resp, filename)
        to_refresh = list(new_resp['studies'])
        return to_refresh, new_resp


    def download_nexson_from_phylografter(self, paths, phylografter):
        download_db, lock_policy = self.download_db, self.lock_policy
        nexson_path = paths['nexson']
        lockfile = nexson_path + '.lock'
        was_locked, owns_lock = lock_policy.wait_for_lock(lockfile)
        try:
            if not owns_lock:
                return None
            study = paths['study']
            er = phylografter.fetch_study(study)
            should_write = False
            if not os.path.exists(nexson_path):
                should_write = True
            else:
                prev_content = json.load(codecs.open(nexson_path, 'rU', encoding='utf-8'))
                if prev_content != er:
                    should_write = True
            if should_write:
                store_state_JSON(er, nexson_path)
            if download_db is not None:
                try:
                    download_db['studies'].remove(int(study))
                except:
                    _LOG.warn('%s not in %s' % (study, paths['nexson_state_db']))
                    pass
                else:
                    store_state_JSON(download_db, paths['nexson_state_db'])
        finally:
            lock_policy.remove_lock()
        return er

    def record_sha_for_study(self,
                             merged_studies,
                             unmerged_study_to_sha,
                             last_merged_sha):
        '''So that the edit history of a file is accurate, we need to store the new parent SHA for any
        future updates. For studies that merged to master, this will be the last_merged_sha. 
        Other studies should be in the unmerged_study_to_sha dict
        '''
        pass
