#!/usr/bin/env python
'''Combinations of git actions used as the opentree git porcelain
'''
from sh import git
from locket import LockError
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

class GitWorkflowError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

def acquire_lock_raise(git_action, fail_msg=''):
    '''Adapts LockError to HTTP. If an exception is not thrown, the git_action has the lock (and must release it!)
    '''
    try:
        git_action.acquire_lock()
    except LockError, e:
        msg = '{o} Details: {d}'.format(o=fail_msg, d=e.message)
        _LOG.debug(msg)
        raise GitWorkflowError(msg)


def _pull_gh(git_action, branch_name):#
    try:
        git_env = git_action.env()
        # TIMING = api_utils.log_time_diff(_LOG, 'lock acquisition', TIMING)
        git(git_action.gitdir, "fetch", git_action.repo_remote, _env=git_env)
        git(git_action.gitdir, git_action.gitwd, "merge", git_action.repo_remote + '/' + branch_name, _env=git_env)
        # TIMING = api_utils.log_time_diff(_LOG, 'git pull', TIMING)
    except Exception, e:
        # We can ignore this if the branch doesn't exist yet on the remote,
        # otherwise raise a 400
#            raise #@EJM what was this doing?
        if "not something we can merge" not in e.message:
            # Attempt to abort a merge, in case of conflicts
            try:
                git(git_action.gitdir,"merge", "--abort")
            except:
                pass
            msg = "Could not pull or merge latest %s branch from %s ! Details: \n%s" % (branch_name, git_action.repo_remote, e.message)
            _LOG.debug(msg)
            raise GitWorkflowError(msg)


def _push_gh(git_action, branch_name, resource_id):#
    try:
        git_env = git_action.env()
        # actually push the changes to Github
        git_action.push(git_action.repo_remote, env=git_env, branch=branch_name)
    except Exception, e:
        raise GitWorkflowError("Could not push deletion of study #%s! Details:\n%s" % (resource_id, e.message))


def commit_and_try_merge2master(git_action, gh, file_content, author_name, author_email, resource_id):
    """Actually make a local Git commit and push it to our remote
    """
    # global TIMING
    author  = "%s <%s>" % (author_name, author_email)
    gh_user = gh.get_user().login
#    git_action.commit_and_try_merge2master(gh_user, file_content, resource_id, author)
#
#def _commit_and_try_merge2master(git_action, gh_user, file_content, resource_id, author):
    branch_name  = "%s_study_%s" % (gh_user, resource_id)
#    fc = git_action._write_temp(file_content)
    try:
        acquire_lock_raise(git_action, fail_msg="Could not acquire lock to write to study #{s}".format(s=resource_id))
        try:
            git_action.checkout_master()
            _pull_gh(git_action, "master")
            
            try:
                new_sha = git_action.write_study(resource_id, file_content, branch_name,author)
                # TIMING = api_utils.log_time_diff(_LOG, 'writing study', TIMING)
            except Exception, e:
                raise GitWorkflowError("Could not write to study #%s ! Details: \n%s" % (resource_id, e.message))
            git_action.merge(branch_name)
            _push_gh(git_action, "master", resource_id)
        finally:
            git_action.release_lock()
    finally:
        pass # fc.close()

    # What other useful information should be returned on a successful write?
    return {
        "error": 0,
        "resource_id": resource_id,
        "branch_name": branch_name,
        "description": "Updated study #%s" % resource_id,
        "sha":  new_sha
    }


def delete_and_push(git_action, gh, author_name, author_email, resource_id):
    author = "%s <%s>" % (author_name, author_email)
    branch_name  = "%s_study_%s" % (gh.get_user().login, resource_id)
    acquire_lock_raise(git_action, fail_msg="Could not acquire lock to delete the study #%s" % resource_id)
    try:
        _pull_gh(git_action, branch_name)
        try:
            pass
            new_sha = git_action.remove_study(resource_id, branch_name, author)
        except Exception, e:
            raise GitWorkflowError("Could not remove study #%s! Details: %s" % (resource_id, e.message))
        _push_gh(git_action, branch_name, resource_id)
    finally:
        git_action.release_lock()
    return {
        "error": 0,
        "branch_name": branch_name,
        "description": "Deleted study #%s" % resource_id,
        "sha":  new_sha
    }