#!/usr/bin/env python
from peyotl.utility.io import open_for_group_write
from peyotl.phylografter.nexson_workaround import workaround_phylografter_nexson
from peyotl.nexson_syntax import read_as_json
import datetime
import codecs
import copy
import json
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



def get_previous_set_of_dirty_nexsons(dir_dict):
    '''Returns the previous list of studies to be fetch and dict that contains that list and timestamps.
    The dict will be populated from the filepath `dir_dict['nexson_state_db']` if that entry is not
    found then a default dict of no studies and old timestamps will be returned.
    '''
    filename = dir_dict['nexson_state_db']
    if os.path.exists(filename):
        old = json.load(codecs.open(filename, 'rU', encoding='utf-8'))
        if 'to_download_from_pg' in old:
            old['to_download_from_pg'] = set(old['to_download_from_pg'])
        if 'to_upload_to_phylesystem' in old:
            old['to_upload_to_phylesystem'] = set(old['to_upload_to_phylesystem'])
    else:
        assert False
        old = {'from': '2010-01-01T00:00:00',
               'to': datetime.datetime.now(),
               'to_download_from_pg': [],
               'to_upload_to_phylesystem': [],
        }
    return set(old['to_download_from_pg']), old

def store_state_JSON(s, fp):
    tmpfilename = fp + '.tmpfile'
    sc = copy.deepcopy(s)
    sc['to_download_from_pg'] = list(s.get('to_download_from_pg', []))
    sc['to_download_from_pg'].sort()
    sc['to_upload_to_phylesystem'] = list(s.get('to_upload_to_phylesystem', []))
    sc['to_upload_to_phylesystem'].sort()
    td = open_for_group_write(tmpfilename, 'w')
    try:
        json.dump(sc, td, sort_keys=True, indent=0)
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
        self.phylesystem_api = api_wrapper.phylesystem_api
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
        if self.download_db is not None:
            self.download_db.setdefault('to_download_from_pg', set()).add(str(study))
            store_state_JSON(self.download_db, paths['nexson_state_db'])
    def _add_study_to_push_list(self, study, paths):
        if self.download_db is not None:
            self.download_db.setdefault('to_upload_to_phylesystem', set()).add(str(study))
            store_state_JSON(self.download_db, paths['nexson_state_db'])
    def _remove_study_from_download_list(self, study, paths):
        if self.download_db is not None:
            try:
                self.download_db.setdefault('to_download_from_pg', set()).remove(str(study))
            except:
                pass
            else:
                store_state_JSON(self.download_db, paths['nexson_state_db'])
    def _remove_study_from_push_list(self, study, paths):
        if self.download_db is not None:
            try:
                self.download_db.setdefault('to_upload_to_phylesystem', set()).remove(str(study))
            except:
                pass
            else:
                store_state_JSON(self.download_db, paths['nexson_state_db'])
    def _get_to_push_list(self):
        if self.download_db is None:
            return []
        return list(self.download_db.setdefault('to_upload_to_phylesystem', set()))
    def find_parent_sha_for_phylografter_nexson(self, study_id, nexson):
        parent_commit_sha = nexson.get('phylesystem_commit_sha')
        if parent_commit_sha is None:
            # as a workaround for phylografter not storing the SHA....
            if self.download_db is not None:
                parent_commit_sha = self.download_db.get('study2sha', {}).get(study_id)
        if parent_commit_sha is None:
            if self.download_db is not None:
                parent_commit_sha = self.download_db.get('default_sha')
        return parent_commit_sha
    def run(self, to_download=None):
        '''Returns the # of studies updated from phylografter to the "NexSON API"

        `to_download` can be a list of study IDs (if the state is not to be preserved). If this call
            uses the history in `cfg_file_paths['nexson_state_db']` then this should be None.
        '''
        self._reset_log()
        if to_download is None:
            to_download, self.download_db = self.get_list_of_phylografter_dirty_nexsons()
        else:
            self.download_db = None
        num_downloaded = len(to_download)
        studies_with_final_sha = set()
        unmerged_study_to_sha = {}
        last_merged_sha = None
        phylografter = self.phylografter
        first_download = True
        self.phylesystem_api_studies = set(self.phylesystem_api.study_list())
        try:
            while len(to_download) > 0:
                if not first_download:
                    time.sleep(self.sleep_between_downloads)
                first_download = False
                n = to_download.pop(0)
                study = str(n)
                paths = get_processing_paths_from_prefix(study, **self._cfg)
                nexson = self.download_nexson_from_phylografter(paths, phylografter)
                if nexson is None:
                    self._failed_study(study, 'pull_from_phylografter_failed')
                    continue
                self._add_study_to_push_list(study, paths)
                self._remove_study_from_download_list(study, paths)
                last_merged_sha = self._do_push_to_phylesystem(study,
                                                               nexson,
                                                               paths,
                                                               unmerged_study_to_sha,
                                                               studies_with_final_sha,
                                                               last_merged_sha)
            tpl = self._get_to_push_list()
            tpl.sort()
            while len(tpl) > 0:
                study = tpl.pop()
                paths = get_processing_paths_from_prefix(study, **self._cfg)
                nexson = self._read_cached_or_refetch(paths, phylografter)
                last_merged_sha = self._do_push_to_phylesystem(study,
                                                               nexson,
                                                               paths,
                                                               unmerged_study_to_sha,
                                                               studies_with_final_sha,
                                                               last_merged_sha)
        finally:
            state_db = self._get_nexson_state_db_fp()
            self.record_sha_for_study(studies_with_final_sha,
                                      unmerged_study_to_sha,
                                      last_merged_sha,
                                      state_db)
        return num_downloaded
    def _get_nexson_state_db_fp(self):
        paths = get_processing_paths_from_prefix('9', **self._cfg)
        return paths['nexson_state_db']
    def _save_state(self):
        if self.download_db is not None:
            store_state_JSON(self.download_db, self._get_nexson_state_db_fp())

    def _do_push_to_phylesystem(self,
                                study,
                                nexson,
                                paths,
                                unmerged_study_to_sha,
                                studies_with_final_sha,
                                last_merged_sha):
        namespaced_id = 'pg_{s}'.format(s=study)
        parent_sha = self.find_parent_sha_for_phylografter_nexson(study, nexson)
        # correct any disagreements between phylografter and what the peyotl 
        #   validator expects...
        workaround_phylografter_nexson(nexson) 
        if namespaced_id in self.phylesystem_api_studies:
            put_response = self.phylesystem_api.put_study(study_id=namespaced_id,
                                                    nexson=nexson,
                                                    starting_commit_sha=parent_sha,
                                                    commit_msg='Sync from phylografter')
            ds_verb = 'PUT'
        else:
            put_response = self.phylesystem_api.post_study(nexson=nexson,
                                                     study_id=namespaced_id,
                                                     commit_msg='Sync from phylografter')
            ds_verb = 'POST'
        if put_response['error'] != 0:
            self._failed_study(study, '{}_to_docstore_failed'.format(ds_verb))
            _LOG.debug('response = ' + str(put_response))
        else:
            if put_response['merge_needed']:
                unmerged_study_to_sha[study] = put_response['sha']
            else:
                studies_with_final_sha.add(study)
                last_merged_sha = put_response['sha']
            self._remove_study_from_push_list(study, paths)
        return last_merged_sha
    def get_list_of_phylografter_dirty_nexsons(self):
        '''Returns a pair: the list of studies that need to be fetched from phylografter
        and a dict that can be serialized to disk in .sync_status.json to cache the details
        of the last call to phylografter's study/modified_list service.

        If PHYLOGRAFTER_DOMAIN_PREF is in the env, it will provide the domain the default
            is the main phylografter site.
        '''
        dir_dict, phylografter = self._cfg, self.phylografter
        filename = dir_dict['nexson_state_db']
        old_set, old = get_previous_set_of_dirty_nexsons(dir_dict)
        new_resp = phylografter.get_modified_list(old['to'], list_only=False)
        ss = set([str(i) for i in new_resp['studies']])
        ss.update(old_set)
        old['to_download_from_pg'] = ss
        old['to'] = new_resp['to']
        store_state_JSON(old, filename)
        to_refresh = list(old['to_download_from_pg'])
        to_refresh.sort()
        return to_refresh, old

    def _read_cached_or_refetch(self, paths, phylografter):
        lock_policy = self.lock_policy
        nexson_path = paths['nexson']
        lockfile = nexson_path + '.lock'
        owns_lock = lock_policy.wait_for_lock(lockfile)[1]
        nexson = None
        try:
            if os.path.exists(nexson_path):
                nexson = read_as_json(nexson_path)
        finally:
            if owns_lock:
                lock_policy.remove_lock()
        if nexson is None:
            return self.download_nexson_from_phylografter(paths, phylografter)
        return nexson

    def download_nexson_from_phylografter(self, paths, phylografter):
        download_db, lock_policy = self.download_db, self.lock_policy
        nexson_path = paths['nexson']
        lockfile = nexson_path + '.lock'
        owns_lock = lock_policy.wait_for_lock(lockfile)[1]
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
                    download_db['to_download_from_pg'].remove(str(study))
                except:
                    _LOG.warn('%s not in %s', repr(study), paths['nexson_state_db'])
                else:
                    store_state_JSON(download_db, paths['nexson_state_db'])
        finally:
            lock_policy.remove_lock()
        return er

    def record_sha_for_study(self,
                             merged_studies,
                             unmerged_study_to_sha,
                             last_merged_sha,
                             state_db):
        '''So that the edit history of a file is accurate, we need to store the new parent SHA for any
        future updates. For studies that merged to master, this will be the last_merged_sha.
        Other studies should be in the unmerged_study_to_sha dict
        '''
        if self.download_db is None:
            return
        _EMPTY_DICT = {}
        for study_id in merged_studies:
            self.download_db.setdefault('study2sha', _EMPTY_DICT)[study_id] = last_merged_sha
        if unmerged_study_to_sha:
            self.download_db.setdefault('study2sha', _EMPTY_DICT).update(unmerged_study_to_sha)
        store_state_JSON(self.download_db, state_db)

