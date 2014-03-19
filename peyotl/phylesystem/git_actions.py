from sh import git
import sh
import re
import os
import locket
import codecs
from peyotl.phylesystem import get_HEAD_SHA1
from peyotl import get_logger
import shutil
import json
from peyotl.nexson_syntax import write_as_json

_LOG = get_logger(__name__)
class MergeException(Exception):
    pass


class GitAction(object):
    def __init__(self, repo, remote=None, git_ssh=None, pkey=None):
        """Create a GitAction object to interact with a Git repository

        Example:
        gd   = GitAction(repo="/home/user/git/foo")

        Note that this requires write access to the
        git repository directory, so it can create a
        lockfile in the .git directory.

        """
        self.repo = repo
        self.git_dir = os.path.join(repo, '.git')
        self.lock_file = os.path.join(self.git_dir, "API_WRITE_LOCK")
        self.lock_timeout = 30
        self.lock = locket.lock_file(self.lock_file, timeout=self.lock_timeout)
        self.repo_remote = remote
        self.git_ssh = git_ssh
        self.pkey = pkey
        
        if os.path.isdir("{}/.git".format(self.repo)):
            self.gitdir = "--git-dir={}/.git".format(self.repo)
            self.gitwd = "--work-tree={}".format(self.repo)
        else: #EJM needs a test?
            raise ValueError('Repo "{repo}" is not a git repo'.format(repo=self.repo))

    def env(self):
        return {'GIT_SSH': self.git_ssh,
                'PKEY': self.pkey,
                }

    def acquire_lock(self):
        "Acquire a lock on the git repository"
        _LOG.debug('Acquiring lock')
        self.lock.acquire()

    def release_lock(self):
        "Release a lock on the git repository"
        _LOG.debug('Releasing lock')
        try:
            self.lock.release()
        except:
            _LOG.debug('Exception releasing lock suppressed.')
            pass

    def current_branch(self):
        "Return the current branch name"
        branch_name = git(self.gitdir, self.gitwd, "symbolic-ref", "HEAD")
        return branch_name.replace('refs/heads/', '').strip()

    def checkout_master(self):
        git(self.gitdir, self.gitwd, "checkout", "master")

    def newest_study_id(self):
        "Return the numeric part of the newest study_id"
        git(self.gitdir, self.gitwd, "checkout", "master")
        dirs = []
        # first we look for studies already in our master branch
        _study_dir = os.path.join(self.repo, "study")
        for f in os.listdir(_study_dir):
            if os.path.isdir(os.path.join(_study_dir, f)):
                # ignore alphabetic prefix, o = created by opentree API
                if f[0].isalpha():
                    dirs.append(int(f[1:]))
                else:
                    dirs.append(int(f))

        # next we must look at local branch names for new studies
        # without --no-color we get terminal color codes in the branch output
        branches = git(self.gitdir, self.gitwd, "branch", "--no-color")
        branches = [ b.strip() for b in branches ]
        for b in branches:
            mo = re.match(".+_o(\d+)", b)
            if mo:
                dirs.append(int(mo.group(1)))
        dirs.sort()
        return dirs[-1]

    def return_study(self, study_id): 
        """Return the contents of the given study_id, and the SHA1 of the HEAD.

        If the study_id does not exist, it returns the empty string.
        """
        study_filename = "%s/study/%s/%s.json" % (self.repo, study_id, study_id)
        head_sha = get_HEAD_SHA1(self.git_dir)
        try:
            f = codecs.open(study_filename, mode='rU', encoding='utf-8')
        except:
            return '', head_sha
        return f.read(), head_sha

    def branch_exists(self, branch):
        """Returns true or false depending on if a branch exists"""
        try:
            git(self.gitdir, self.gitwd, "rev-parse", branch)
        except sh.ErrorReturnCode:
            return False
        return True

    def _find_head_sha(self, gh_user, resource_id, parent_sha):
        head_shas = git(self.gitdir, self.gitwd, "show-ref")
        for lin in head_shas:
            if lin.startswith(parent_sha):
                if gh_user in lin.split()[1] and resource_id in lin.split()[1] :
                     branch = lin.split()[1].split('/')[-1]
                     return branch
        else:
            return None    


    def create_or_checkout_branch(self, gh_user, resource_id, parent_sha):
        branch = self._find_head_sha(gh_user, resource_id, parent_sha)
        if branch:
            git(self.gitdir, self.gitwd, "checkout", branch)
        else:
            branch = "{ghu}_study_{rid}".format(ghu=gh_user, rid=resource_id)
            i=1
            while self.branch_exists(branch):
                branch = "{ghu}_study_{rid}_{i}".format(ghu=gh_user, rid=resource_id, i=i)
                i+=1
            try:
                git(self.gitdir, self.gitwd, "branch", branch, parent_sha)
            except:
                raise ValueError('parent sha not in git repo')
        return branch


    def remove_study(self, gh_user, resource_id, parent_sha, author="OpenTree API <api@opentreeoflife.org>"):
        """Remove a study
        Given a study_id, branch and optionally an
        author, remove a study on the given branch
        and attribute the commit to author.
        Returns the SHA of the commit on branch.
        """
        study_dir = "{r}/study/{id}".format(r=self.repo, id=resource_id) #TODO change directory
        study_filename = "{d}/{id}.json".format(d=study_dir, id=resource_id)

        branch = self.create_or_checkout_branch(gh_user, resource_id, parent_sha)
        if not os.path.isdir(study_dir):
            # branch already exists locally with study removed
            # so just return the commit SHA
            return git(self.gitdir, self.gitwd, "rev-parse", "HEAD").strip(), branch
        git(self.gitdir, self.gitwd, "rm", "-rf", study_dir)
        git(self.gitdir, self.gitwd, "commit", author=author, message="Delete Study #%s via OpenTree API" % resource_id)
        new_sha = git(self.gitdir, self.gitwd, "rev-parse", "HEAD")
        return new_sha.strip(), branch
        



    def write_study(self, study_id, tmpfi, gh_user, resource_id, parent_sha, author="OpenTree API <api@opentreeoflife.org>"): #@EJM don't forget to fix!!

        """Write a study

        Given a study_id, temporary filename of content, branch and
        optionally an author, write a study on the
        given branch and attribute the commit to
        author. If the branch does not yet exist,
        it will be created. If the study is being
        created, it's containing directory will be
        created as well.
        Returns the SHA of the new commit on branch.

        """
        study_dir      = "{}/study/{}".format(self.repo, study_id) #TODO EJM change directory
        study_filename = "{}/{}.json".format(study_dir, study_id) 

        branch = self.create_or_checkout_branch(gh_user, resource_id, parent_sha)
        
        # create a study directory if this is a new study EJM- what if it isn't?
        if not os.path.isdir(study_dir):
            os.mkdir(study_dir)
            
        shutil.copy(tmpfi.name, study_filename)
        
        git(self.gitdir, self.gitwd, "add",study_filename)
        try:
          git(self.gitdir, self.gitwd,  "commit", author=author, message="Update Study #%s via OpenTree API" % study_id)
        except Exception, e:
            # We can ignore this if no changes are new,
            # otherwise raise a 400
            if "nothing to commit" in e.message:#@EJM is this dangerous?
                 pass
            else:
                 raise
                 
        new_sha = git(self.gitdir, self.gitwd,  "rev-parse", "HEAD")

        return new_sha.strip(), branch

    def merge(self, branch, base_branch="master"):
        """
        Merge the the given WIP branch to master (or base_branch, if specified)

        If the merge fails, the merge will be aborted
        and then a MergeException will be thrown. The
        message of the MergeException will be the
        "git status" output, so details about merge
        conflicts can be determined.

        """

        current_branch = self.current_branch()
        if current_branch != base_branch:
            git(self.gitdir, self.gitwd, "checkout", base_branch)

        # Always create a merge commit, even if we could fast forward, so we know
        # when merges occured
        try:
            merge_output = git(self.gitdir, self.gitwd, "merge",  "--no-ff", branch)
        except sh.ErrorReturnCode:
            raise
            # attempt to reset things so other operations can
            # continue
            output = git(self.gitdir, self.gitwd, "status")
            git(self.gitdir, self.gitwd, "merge", "--abort")

            # re-raise the exception so other code can decide
            # what to do with it
            raise MergeException(output)

        # the merge succeeded, so remove the local WIP branch
        git(self.gitdir, self.gitwd, "branch", "-d", branch)

        new_sha      = git(self.gitdir, self.gitwd, "rev-parse", "HEAD")
        return new_sha.strip()
