#!/usr/bin/env python
import locket
import sys
import os

repo = sys.argv[1]
git_dir = os.path.join(repo, '.git')
assert os.path.isdir(git_dir)
lf = os.path.join(git_dir, "API_WRITE_LOCK")
with locket.lock_file(lf, timeout=10):
    print 'Lock acquired. Use Control-D to release'
    x = sys.stdin.read()
    print 'released'
    sys.exit(0)
sys.exit('timeout waiting for lock\n')