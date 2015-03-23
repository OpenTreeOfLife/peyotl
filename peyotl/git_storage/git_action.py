"""Base class git action manager (subclasses will accommodate each type)"""
import os
from sh import git

def get_HEAD_SHA1(git_dir):
    '''Not locked!
    '''
    head_file = os.path.join(git_dir, 'HEAD')
    with open(head_file, 'r') as hf:
        head_contents = hf.read().strip()
    assert head_contents.startswith('ref: ')
    ref_filename = head_contents[5:] #strip off "ref: "
    real_ref = os.path.join(git_dir, ref_filename)
    with open(real_ref, 'r') as rf:
        return rf.read().strip()

def get_user_author(auth_info):
    '''Return commit author info from a dict. Returns username and author string.

    auth_info should have 3 strings:
        `login` (a github log in)
        `name`
        `email`
    username will be in the `login` value. It is used for WIP branch naming.
    the author string will be the name and email joined. This is used in commit messages.
    '''
    return auth_info['login'], ("%s <%s>" % (auth_info['name'], auth_info['email']))

class MergeException(Exception):
    pass

class GitWorkflowError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class RepoLock(object):
    def __init__(self, lock):
        self._lock = lock
    def __enter__(self):
        self._lock.acquire()
    def __exit__(self, _type, value, traceb):
        self._lock.release()

class GitActionBase(object):
    @staticmethod
    def clone_repo(par_dir, repo_local_name, remote):
        if not os.path.isdir(par_dir):
            raise ValueError(repr(par_dir) + ' is not a directory')
        if not is_str_type(remote):
            raise ValueError(repr(remote) + ' is not a remote string')
        dest = os.path.join(par_dir, repo_local_name)
        if os.path.exists(dest):
            raise RuntimeError('Filepath "{}" is in the way'.format(dest))
        git('clone', remote, repo_local_name, _cwd=par_dir)
    @staticmethod
    def add_remote(repo_dir, remote_name, remote_url):
        git_dir_arg = "--git-dir={}/.git".format(repo_dir)
        git(git_dir_arg, 'remote', 'add', remote_name, remote_url)

    def __init__(self):
        pass
