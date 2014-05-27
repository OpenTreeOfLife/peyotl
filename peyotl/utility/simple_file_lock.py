#!/usr/bin/env python
from peyotl.utility.io import open_for_group_write
import time
import os
from peyotl import get_logger
_LOG = get_logger(__name__)

class LockPolicy(object):
    def __init__(self, sleep_time=0.05, max_num_sleep=100):
        self.early_exit_if_locked = False
        self.wait_do_not_relock_if_locked = False
        self.sleep_time = sleep_time
        self.max_num_sleep = max_num_sleep
        self._reset_current()
    def _reset_current(self):
        self.curr_lockfile, self.curr_owns_lock, self.curr_was_locked = False, False, False
    def _wait_for_lock(self, lockfile):
        '''Returns a pair of bools: lockfile previously existed, lockfile now owned by caller
        '''
        n = 0
        par_dir = os.path.split(lockfile)[0]
        if not os.path.exists(par_dir):
            os.makedirs(par_dir)
        pid = os.getpid()
        previously_existed = False
        while os.path.exists(lockfile):
            previously_existed = True
            n += 1
            if self.early_exit_if_locked or n > self.max_num_sleep:
                return True, False
            _LOG.debug('Waiting for "%s" iter %d\n', lockfile, n)
            time.sleep(self.sleep_time)
        if previously_existed and self.wait_do_not_relock_if_locked:
            return True, False
        try:
            o = open_for_group_write(lockfile, 'w')
            o.write(str(pid) + '\n')
            o.close()
        except:
            _LOG.exception('Could not create lockfile.')
            try:
                self._remove_lock(lockfile)
            except:
                _LOG.exception('Could not remove lockfile.')
            return previously_existed, False
        else:
            return previously_existed, True
    def wait_for_lock(self, lockfile):
        t = self._wait_for_lock(lockfile)
        self.curr_lockfile = lockfile
        self.curr_was_locked, self.curr_owns_lock = t
        _LOG.debug('Lockfile = "%s" was_locked=%s owns_lock=%s\n',
                    lockfile,
                    "TRUE" if self.curr_was_locked else "FALSE",
                    "TRUE" if self.curr_owns_lock else "FALSE")
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

