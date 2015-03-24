"""Base class git action manager (subclasses will accommodate each type)"""
from peyotl.utility.str_util import is_str_type
from peyotl.utility import get_logger
import os
from sh import git
import sh
import locket
import codecs

_LOG = get_logger(__name__)

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

    def __init__(self,
                 repo,
                 remote=None,
                 git_ssh=None,
                 pkey=None,
                 cache=None, #pylint: disable=W0613
                 path_for_doc_fn=None,
                 max_file_size=None,
                 path_for_doc_id_fn=None):
        self.repo = repo
        self.git_dir = os.path.join(repo, '.git')
        self._lock_file = os.path.join(self.git_dir, "API_WRITE_LOCK")
        self._lock_timeout = 30  #TODO:type-specific?
        self._lock = locket.lock_file(self._lock_file, timeout=self._lock_timeout)
        self.repo_remote = remote
        self.git_ssh = git_ssh
        self.pkey = pkey
        self.max_file_size = max_file_size
        self.path_for_doc_fn = path_for_doc_fn
        self.path_for_doc_id_fn = path_for_doc_id_fn
        if os.path.isdir("{}/.git".format(self.repo)):
            self.gitdir = "--git-dir={}/.git".format(self.repo)
            self.gitwd = "--work-tree={}".format(self.repo)
        else: #EJM needs a test?
            raise ValueError('Repo "{repo}" is not a git repo'.format(repo=self.repo))
    def env(self): #@TEMP could be ref to a const singleton.
        d = dict(os.environ)
        if self.git_ssh:
            d['GIT_SSH'] = self.git_ssh
        if self.pkey:
            d['PKEY'] = self.pkey
        return d
    def acquire_lock(self):
        "Acquire a lock on the git repository"
        _LOG.debug('Acquiring lock')
        self._lock.acquire()
    def release_lock(self):
        "Release a lock on the git repository"
        _LOG.debug('Releasing lock')
        try:
            self._lock.release()
        except:
            _LOG.debug('Exception releasing lock suppressed.')
    def path_for_doc(self, doc_id):
        '''Returns doc_dir and doc_filepath for doc_id.
        '''
        return self.path_for_doc_fn(self.repo, doc_id)
    def lock(self):
        ''' for syntax:
        with git_action.lock():
            git_action.checkout()
        '''
        return RepoLock(self._lock)
    def get_branch_list(self):
        x = git(self.gitdir, self.gitwd, "branch", "--no-color")
        b = []
        for line in x.split('\n'):
            if line.startswith('*'):
                line = line[1:]
            ls = line.strip()
            if ls:
                b.append(ls)
        return b
    def current_branch(self):
        "Return the current branch name"
        branch_name = git(self.gitdir, self.gitwd, "symbolic-ref", "HEAD")
        return branch_name.replace('refs/heads/', '').strip()
    def branch_exists(self, branch):
        """Returns true or false depending on if a branch exists"""
        try:
            git(self.gitdir, self.gitwd, "rev-parse", branch)
        except sh.ErrorReturnCode:
            return False
        return True
    def delete_branch(self, branch):
        git(self.gitdir, self.gitwd, 'branch', '-d', branch)
    def _find_head_sha(self, frag, parent_sha):
        head_shas = git(self.gitdir, self.gitwd, "show-ref", "--heads")
        for lin in head_shas.split('\n'):
            #_LOG.debug("lin = '{l}'".format(l=lin))
            if lin.startswith(parent_sha):
                local_branch_split = lin.split(' refs/heads/')
                #_LOG.debug("local_branch_split = '{l}'".format(l=local_branch_split))
                if len(local_branch_split) == 2:
                    branch = local_branch_split[1].rstrip()
                    if branch.startswith(frag):
                        return branch
        return None
    def checkout(self, branch):
        git(self.gitdir, self.gitwd, "checkout", branch)
    def checkout_master(self):
        git(self.gitdir, self.gitwd, "checkout", "master")
    def fetch(self, remote='origin'):
        '''fetch from a remote'''
        git(self.gitdir, "fetch", remote, _env=self.env())
    def push(self, branch, remote):
        git(self.gitdir, 'push', remote, branch, _env=self.env())
    def reset_hard(self):
        try:
            git(self.gitdir, self.gitwd, 'reset', '--hard')
        except:
            _LOG.exception('"git reset --hard" failed.')
    def get_master_sha(self):
        x = git(self.gitdir, self.gitwd, "show-ref", "master", "--heads", "--hash")
        return x.strip()
    def get_blob_sha_for_file(self, filepath, branch='HEAD'):
        try:
            r = git(self.gitdir, self.gitwd, 'ls-tree', branch, filepath)
            #_LOG.debug('ls-tree said "{}"'.format(r))
            line = r.strip()
            ls = line.split()
            #_LOG.debug('ls is "{}"'.format(str(ls)))
            assert len(ls) == 4
            assert ls[1] == 'blob'
            return ls[2]
        except:
            _LOG.exception('git ls-tree failed')
            raise
    def get_version_history_for_file(self, filepath):
        """ Return a dict representation of this file's commit history

        This uses specially formatted git-log output for easy parsing, as described here:
            http://blog.lost-theory.org/post/how-to-parse-git-log-output/
        For a full list of available fields, see:
            http://linux.die.net/man/1/git-log

        """
        # define the desired fields for logout output, matching the order in these lists!
        GIT_COMMIT_FIELDS = ['id',
                             'author_name',
                             'author_email',
                             'date',
                             'date_ISO_8601',
                             'relative_date',
                             'message_subject',
                             'message_body']
        GIT_LOG_FORMAT = ['%H', '%an', '%ae', '%aD', '%ai', '%ar', '%s', '%b']
        # make the final format string, using standard ASCII field/record delimiters
        GIT_LOG_FORMAT = '%x1f'.join(GIT_LOG_FORMAT) + '%x1e'
        try:
            log = git(self.gitdir,
                      self.gitwd,
                      '--no-pager',
                      'log',
                      '--format=%s' % GIT_LOG_FORMAT,
                      '--follow',               # Track file's history when moved/renamed...
                      '--find-renames=100%',    # ... but only if the contents are identical!
                      '--',
                      filepath)
            #_LOG.debug('log said "{}"'.format(log))
            log = log.strip('\n\x1e').split("\x1e")
            log = [row.strip().split("\x1f") for row in log]
            log = [dict(zip(GIT_COMMIT_FIELDS, row)) for row in log]
        except:
            _LOG.exception('git log failed')
            raise
        return log
    def _add_and_commit(self, doc_filepath, author, commit_msg):
        '''Low level function used internally when you have an absolute filepath to add and commit'''
        try:
            git(self.gitdir, self.gitwd, "add", doc_filepath)
            git(self.gitdir, self.gitwd, "commit", author=author, message=commit_msg)
        except Exception as e:
            # We can ignore this if no changes are new,
            # otherwise raise a 400
            if "nothing to commit" in e.message:#@EJM is this dangerous?
                _LOG.debug('"nothing to commit" found in error response')
            else:
                _LOG.exception('"git commit" failed')
                self.reset_hard()
                raise
    def merge(self, branch, destination="master"):
        """
        Merge the the given WIP branch to master (or destination, if specified)

        If the merge fails, the merge will be aborted
        and then a MergeException will be thrown. The
        message of the MergeException will be the
        "git status" output, so details about merge
        conflicts can be determined.
        """
        current_branch = self.current_branch()
        if current_branch != destination:
            _LOG.debug('checking out ' + destination)
            git(self.gitdir, self.gitwd, "checkout", destination)
        try:
            git(self.gitdir, self.gitwd, "merge", branch)
        except sh.ErrorReturnCode:
            _LOG.exception('merge failed')
            # attempt to reset things so other operations can continue
            git(self.gitdir, self.gitwd, "merge", "--abort")
            # raise an MergeException so that caller will know that the merge failed
            raise MergeException()

        new_sha = git(self.gitdir, self.gitwd, "rev-parse", "HEAD")
        return new_sha.strip()
    def return_doc(self, doc_id, branch='master', commit_sha=None, return_WIP_map=False):
        """Return the
            blob[0] contents of the given doc_id,
            blob[1] the SHA1 of the HEAD of branch (or `commit_sha`)
            blob[2] dictionary of WIPs for this doc.
        If the doc_id does not exist, it returns the empty string.
        If `commit_sha` is provided, that will be checked out and returned.
            otherwise the branch will be checked out.
        """
        #_LOG.debug('return_doc({s}, {b}, {c}...)'.format(s=doc_id, b=branch, c=commit_sha))
        if commit_sha is None:
            self.checkout(branch)
            head_sha = get_HEAD_SHA1(self.git_dir)
        else:
            self.checkout(commit_sha)
            head_sha = commit_sha
        doc_filepath = self.path_for_doc(doc_id)
        try:
            f = codecs.open(doc_filepath, mode='r', encoding='utf-8')
            content = f.read()
        except:
            content = None
        if return_WIP_map:
            d = self.find_WIP_branches(doc_id)
            return content, head_sha, d
        return content, head_sha
