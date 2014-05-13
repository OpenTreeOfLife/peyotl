#!/usr/bin/env python
import codecs
import json
import os
import requests
import stat
import sys
import time
from peyotl import get_logger
_LOG = get_logger(__name__)

class LockPolicy(object):
    MAX_NUM_SLEEP_IN_WAITING_FOR_LOCK = os.environ.get('MAX_NUM_SLEEP_IN_WAITING_FOR_LOCK', 100)
    try:
        SLEEP_FOR_LOCK_TIME = float(os.environ.get('SLEEP_FOR_LOCK_TIME', 0.05))
    except:
        SLEEP_FOR_LOCK_TIME = 0.05 

    def __init__(self):
        self.early_exit_if_locked = False
        self.wait_do_not_relock_if_locked = False
        self._reset_current()

    def _reset_current(self):
        self.curr_lockfile, self.curr_owns_lock, self.curr_was_locked = False, False, False

    def _wait_for_lock(self, lockfile):
        '''Returns a pair of bools: lockfile previously existed, lockfile now owned by caller
        '''
        n = 0
        pid = os.getpid()
        previously_existed = False
        while os.path.exists(lockfile):
            previously_existed = True
            n += 1
            if self.early_exit_if_locked or n > LockPolicy.MAX_NUM_SLEEP_IN_WAITING_FOR_LOCK:
                return True, False
            if VERBOSE:
                sys.stderr.write('Waiting for "%s" iter %d\n' % (lockfile, n))
            time.sleep(LockPolicy.SLEEP_FOR_LOCK_TIME)
        if previously_existed and self.wait_do_not_relock_if_locked:
            return True, False
        try:
            o = open_for_group_write(lockfile, 'w')
            o.write(str(pid) + '\n')
            o.close()
        except:
            try:
                self.remove_lock(lockfile)
            except:
                pass
            return previously_existed, False
        else:
            return previously_existed, True
    def wait_for_lock(self, lockfile):
        t = self._wait_for_lock(lockfile)
        self.curr_lockfile = lockfile
        self.curr_was_locked, self.curr_owns_lock = t
        _LOG.debug('Lockfile = "%s" was_locked=%s owns_lock=%s\n'% 
                    (lockfile, 
                     "TRUE" if self.curr_was_locked else "FALSE",
                     "TRUE" if self.curr_owns_lock else "FALSE",
                     ))
        return t
    def remove_lock(self):
        try:
            if self.curr_lockfile and self.curr_owns_lock:
                self._remove_lock(self.curr_lockfile)
        finally:
            self._reset_current()
    def _remove_lock(self, lockfile):
        if os.path.exists(lockfile):
            os.remove(lockfile)



def get_processing_paths_from_prefix(pref,
                                     nexson_dir='.',
                                     nexson_state_db=None):
    d = {'nexson': os.path.abspath(os.path.join(nexson_dir, 'study', pref, pref + '.json')),
         'nexson_state_db': nexson_state_db,
         'study': pref,
         }
    if d['nexson_state_db'] is None:
        d['nexson_state_db'] = os.path.abspath(os.path.join(nexson_dir, '.to_download.json')), # stores the state of this repo. *very* hacky primitive db.
    return d

def get_default_dir_dict(top_level=None):
    r = '.' if top_level is None else top_level
    t = os.path.abspath(r)
    d = {'nexson_dir': t,
         'nexson_state_db': os.path.join(t, '.sync_status.json'), # stores the state of this repo. *very* hacky primitive db.
        }
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

def get_list_of_dirty_nexsons(dir_dict, phylografter):
    '''Returns a pair: the list of studies that need to be fetched from phylografter
    and a dict that can be serialized to disk in .to_download.json to cache the details
    of the last call to phylografter's study/modified_list service.

    If PHYLOGRAFTER_DOMAIN_PREF is in the env, it will provide the domain the default
        is the main phylografter site.
    '''
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


def open_for_group_write(fp, mode):
    '''Open with mode=mode and permissions '-rw-rw-r--' group writable is 
    the default on some systems/accounts, but it is important that it be present on our deployment machine
    '''
    d = os.path.split(fp)[0]
    if not os.path.exists(d):
        os.makedirs(d)
    o = codecs.open(fp, mode, encoding='utf-8')
    o.flush()
    os.chmod(fp, stat.S_IRGRP | stat.S_IROTH | stat.S_IRUSR | stat.S_IWGRP | stat.S_IWUSR)
    return o

def store_state_JSON(s, fp):
    tmpfilename = fp + '.tmpfile'
    td = open_for_group_write(tmpfilename, 'w')
    try:
        json.dump(s, td, sort_keys=True, indent=0)
    finally:
        td.close()
    os.rename(tmpfilename, fp) #atomic on POSIX

def download_nexson_from_phylografter(phylografter,
                                      paths,
                                      download_db,
                                      lock_policy):
    nexson_path = paths['nexson']
    lockfile = nexson_path + '.lock'
    was_locked, owns_lock = lock_policy.wait_for_lock(lockfile)
    try:
        if not owns_lock:
            return False
        study = paths['study']
        er = phylografter.get_study(study)
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
                warn('%s not in %s' % (study, paths['nexson_state_db']))
                pass
            else:
                store_state_JSON(download_db, paths['nexson_state_db'])
    finally:
        lock_policy.remove_lock()
    return True

def sync_from_phylografter2nexson_api(
        api_wrapper, 
        to_download,
        cfg_file_paths,
        download_db_file,
        lock_policy):
    while len(to_download) > 0:
        n = to_download.pop(0)
        study = str(n)
        paths = get_processing_paths_from_prefix(study, **cfg_file_paths)
        if not download_nexson_from_phylografter(api_wrapper.phylografter,
                                                 paths,
                                                 download_db_file,
                                                 lock_policy):
            sys.exit('NexSON "%s" could not be refreshed\n' % paths['nexson'])
        if len(to_download) > 0:
            time.sleep(sleep_between_downloads)

if __name__ == '__main__':
    from peyotl.api import APIDomains
    api_wrapper = APIDomains()
    if '-h' in sys.argv:
        sys.stderr.write('''refresh_nexsons_from_phylografter.py is a short-term hack.

It stores info about the last communication with phylografter in .to_download.json
Based on this info, it tries to download as few studies as possible to make 
the NexSONs in treenexus/studies/#/... match the export from phylografter.

   -h gives this help message.

If other arguments aree supplied, it should be the study #'s to be downloaded.
''')
        sys.exit(0)
    lock_policy = LockPolicy()
    dd = get_default_dir_dict()
    if len(sys.argv) == 1:
        to_download, download_db = get_list_of_dirty_nexsons(dd)
        if not to_download:
            sys.stderr.write('No studies have been modified since the last refresh.\n')
            sys.exit(0)
    else:
        to_download, download_db = sys.argv[1:], None
    try:
        SLEEP_BETWEEN_DOWNLOADS_TIME = float(os.environ.get('SLEEP_BETWEEN_DOWNLOADS_TIME', 0.5))
    except:
        SLEEP_BETWEEN_DOWNLOADS_TIME = 0.05
    sync_from_phylografter2nexson_api(api_wrapper=api_wrapper
                                      to_download=to_download,
                                      cfg_file_paths=dd,
                                      download_db_file=download_db,
                                      lock_policy=lock_policy)

