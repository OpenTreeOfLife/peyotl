#!/usr/bin/env python
'''Combinations of git actions used as the opentree git porcelain
'''
from sh import git
from locket import LockError
import tempfile
from peyotl.nexson_syntax import write_as_json
from peyotl.nexson_validation import NexsonWarningCodes, validate_nexson
from peyotl.nexson_syntax import convert_nexson_format
from peyotl.utility import get_logger
from locket import LockError
from sh import git
import traceback
import json

_LOG = get_logger(__name__)

parent_sha="f5f6101aad47677d41cbb613efaad54136acbe87"

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

def __validate(nexson):
    '''Returns three objects:
        an annotation dict (NexSON formmatted), 
        the validation_log object created when NexSON validation was performed, and
        the object of class NexSON which was created from nexson. This object may
            alias parts of the nexson dict that is passed in as an argument.
    '''
    # stub function for hooking into NexSON validation
    codes_to_skip = [NexsonWarningCodes.UNVALIDATED_ANNOTATION]
    v_log, adaptor = validate_nexson(nexson, codes_to_skip)
    annotation = v_log.prepare_annotation(author_name='api.opentreeoflife.org/validate')
    return annotation, v_log, adaptor

def validate_and_convert_nexson(nexson, output_version, allow_invalid):
    '''Runs the nexson validator and returns a converted 4 object:
        nexson, annotation, validation_log, nexson_adaptor

    `nexson` is the nexson dict.
    `output_version` is the version of nexson syntax to be used after validation.
    if `allow_invalid` is False, and the nexson validation has errors, then
        a GitWorkflowError will be generated before conversion.
    '''
    try:
        annotation, validation_log, nexson_adaptor = __validate(nexson)
    except:
        msg = 'exception in __validate: ' + traceback.format_exc()
        raise GitWorkflowError(msg)
    if (not allow_invalid) and validation_log.has_error():
        raise GitWorkflowError('__validation failed: ' + json.dumps(annotation))
    nexson = convert_nexson_format(nexson, output_version)
    return nexson, annotation, validation_log, nexson_adaptor


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


def _push_gh(git_action, branch_name, resource_id):
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
    return _commit_and_try_merge2master(git_action, gh_user, file_content, resource_id, author, parent_sha)


def _commit_and_try_merge2master(git_action, gh_user, file_content, resource_id, author, parent_sha):
    fc = tempfile.NamedTemporaryFile()
    if isinstance(file_content, str) or isinstance(file_content, unicode):
            fc.write(file_content)
    else:
            write_as_json(file_content, fc)
    fc.flush()
    try:
        acquire_lock_raise(git_action, fail_msg="Could not acquire lock to write to study #{s}".format(s=resource_id))
        try:
            new_sha, branch_name = git_action.write_study(resource_id, fc, gh_user, resource_id, parent_sha, author)
        except Exception, e:
                raise GitWorkflowError("Could not write to study #%s ! Details: \n%s" % (resource_id, e.message))
        git_action.merge(branch_name) #@EJM need to return the branch name...
    finally:
        git_action.release_lock()
        fc.close()
    # What other useful information should be returned on a successful write?
    return {
        "error": 0,
        "resource_id": resource_id,
        "branch_name": branch_name,
        "description": "Updated study #%s" % resource_id,
        "sha":  new_sha
    }


def delete_and_push(git_action, gh, author_name, author_email, resource_id):
    author  = "%s <%s>" % (author_name, author_email)
    gh_user = gh.get_user().login
    acquire_lock_raise(git_action, fail_msg="Could not acquire lock to delete the study #%s" % resource_id)
    try:
        new_sha, branch_name = git_action.remove_study(gh_user, resource_id, parent_sha)
    except Exception, e:
        raise GitWorkflowError("Could not remove study #%s! Details: %s" % (resource_id, e.message))
    finally:
        git_action.release_lock()
    return {
        "error": 0,
        "branch_name": branch_name,
        "description": "Deleted study #%s" % resource_id,
        "sha":  new_sha
    }