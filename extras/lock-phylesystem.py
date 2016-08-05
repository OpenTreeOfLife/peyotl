#!/usr/bin/env python
import locket
import sys
import os

try:
    repo = sys.argv[1]
    git_dir = os.path.join(repo, '.git')
    assert os.path.isdir(git_dir)
except:
    sys.exit('''Expecting a phylesystem shard (or one for collections, amendments, etc.) as the only argument.
This script looks for the .git dir in the first argument, and locks that .git
  dir to prevent simultaneous operations by the phylesystem-api.

An example usage would be:

    $ ssh api
    $ source venv/bin/activate
    $ cd repo/phylesystem-1_par/phylesystem-1
    $ python ~/repo/peyotl/extras/lock-phylesystem.py .
    ...
    <Ctrl-D> to release the lock.

''')
lf = os.path.join(git_dir, "API_WRITE_LOCK")
with locket.lock_file(lf, timeout=10):
    print 'Lock acquired. Use Control-D to release'
    try:
      x = sys.stdin.read()
    finally:
      print 'Lock released'
    sys.exit(0)
sys.exit('timeout waiting for lock\n')
