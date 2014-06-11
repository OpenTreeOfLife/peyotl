#!/usr/bin/env python
'''Combinations of git actions used as the opentree git porcelain
'''
from sh import git
from locket import LockError
import tempfile
from peyotl.nexson_syntax import write_as_json
from peyotl.nexson_validation import ot_validate
from peyotl.nexson_syntax import convert_nexson_format
from peyotl.phylesystem.git_actions import MergeException, \
                                           get_user_author, \
                                           GitWorkflowError
from peyotl.utility import get_logger
from locket import LockError
from sh import git
import traceback
import json
import os


_LOG = get_logger(__name__)

TRACE_FILES = False

def _write_to_next_free(tag, blob):
    '''#WARNING not thread safe just a easy of debugging routine!'''
    ind = 0
    pref = '/tmp/peyotl-' + tag + str(ind)
    while os.path.exists(pref):
        ind += 1
        pref = '/tmp/peyotl-' + tag + str(ind)
    write_as_json(blob, pref)

def acquire_lock_raise(git_action, fail_msg=''):
    '''Adapts LockError to HTTP. If an exception is not thrown, the git_action has the lock (and must release it!)
    '''
    try:
        git_action.acquire_lock()
    except LockError, e:
        msg = '{o} Details: {d}'.format(o=fail_msg, d=e.message)
        _LOG.debug(msg)
        raise GitWorkflowError(msg)

#TODO:validate_and_convert_nexson belong in a different part of peyotl

def validate_and_convert_nexson(nexson, output_version, allow_invalid):
    '''Runs the nexson validator and returns a converted 4 object:
        nexson, annotation, validation_log, nexson_adaptor

    `nexson` is the nexson dict.
    `output_version` is the version of nexson syntax to be used after validation.
    if `allow_invalid` is False, and the nexson validation has errors, then
        a GitWorkflowError will be generated before conversion.
    '''
    try:
        if TRACE_FILES:
            _write_to_next_free('input', nexson)
        annotation, validation_log, nexson_adaptor = ot_validate(nexson)
        if TRACE_FILES:
            _write_to_next_free('annotation', annotation)
    except:
        msg = 'exception in ot_validate: ' + traceback.format_exc()
        raise GitWorkflowError(msg)
    if (not allow_invalid) and validation_log.has_error():
        raise GitWorkflowError('ot_validation failed: ' + json.dumps(annotation))
    nexson = convert_nexson_format(nexson, output_version)
    if TRACE_FILES:
        _write_to_next_free('converted', nexson)
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
                git(git_action.gitdir, "merge", "--abort")
            except:
                pass
            msg_f = "Could not pull or merge latest %s branch from %s ! Details: \n%s"
            msg = msg_f % (branch_name, git_action.repo_remote, e.message)
            _LOG.debug(msg)
            raise GitWorkflowError(msg)


def _do_merge2master_commit(git_action,
                     new_sha,
                     branch_name,
                     study_filepath,
                     merged_sha,
                     prev_file_sha):
    merge_needed = False
    git_action.checkout_master()
    if os.path.exists(study_filepath):
        b = git_action.get_blob_sha_for_file(study_filepath)
        _LOG.debug('master SHA for that file path is {b}'.format(b=b))
    else:
        b = None
    if merged_sha is None:
        same_sha = prev_file_sha
    else:
        same_sha = merged_sha
    if b == same_sha:
        try:
            new_sha = git_action.merge(branch_name, 'master')
        except MergeException:
            _LOG.error('MergeException in a "safe" merge !!!')
            merge_needed = True
        else:
            _LOG.debug('merge to master succeeded')
            git_action.delete_branch(branch_name)
            branch_name = 'master'
    else:
        _LOG.debug('Edit from different source. merge_needed <- True')
        merge_needed = True
    return new_sha, branch_name, merge_needed

def commit_and_try_merge2master(git_action,
                                file_content,
                                study_id,
                                auth_info,
                                parent_sha,
                                commit_msg='',
                                merged_sha=None):
    """Actually make a local Git commit and push it to our remote
    """
    #_LOG.debug('commit_and_try_merge2master study_id="{s}" \
    #            parent_sha="{p}" merged_sha="{m}"'.format(
    #            s=study_id, p=parent_sha, m=merged_sha))
    merge_needed = False
    fc = tempfile.NamedTemporaryFile()
    try:
        if isinstance(file_content, str) or isinstance(file_content, unicode):
            fc.write(file_content)
        else:
            write_as_json(file_content, fc)
        fc.flush()
        f = "Could not acquire lock to write to study #{s}".format(s=study_id)
        acquire_lock_raise(git_action, fail_msg=f)
        try:
            try:
                commit_resp = git_action.write_study_from_tmpfile(study_id, fc, parent_sha, auth_info, commit_msg)
            except Exception, e:
                _LOG.exception('write_study_from_tmpfile exception')
                raise GitWorkflowError("Could not write to study #%s ! Details: \n%s" % (study_id, e.message))
            written_fp = git_action.path_for_study(study_id)
            branch_name = commit_resp['branch']
            new_sha = commit_resp['commit_sha']
            _LOG.debug('write of study {s} on parent {p} returned = {c}'.format(s=study_id,
                                                                                p=parent_sha,
                                                                                c=str(commit_resp)))
            m_resp = _do_merge2master_commit(git_action,
                                             new_sha,
                                              branch_name,
                                              written_fp,
                                              merged_sha=merged_sha,
                                              prev_file_sha=commit_resp.get('prev_file_sha'))
            new_sha, branch_name, merge_needed = m_resp
        finally:
            git_action.release_lock()
    finally:
        fc.close()
    # What other useful information should be returned on a successful write?
    r = {
        "error": 0,
        "resource_id": study_id,
        "branch_name": branch_name,
        "description": "Updated study #%s" % study_id,
        "sha":  new_sha,
        "merge_needed": merge_needed,
    }
    _LOG.debug('returning {r}'.format(r=str(r)))
    return r

def delete_study(git_action, study_id, auth_info, parent_sha, commit_msg='', merged_sha=None):
    author = "{} <{}>".format(auth_info['name'], auth_info['email'])
    gh_user = auth_info['login']
    acquire_lock_raise(git_action, fail_msg="Could not acquire lock to delete the study #%s" % study_id)
    try:
        study_fp = git_action.path_for_study(study_id)
        rs_resp = git_action.remove_study(gh_user, study_id, parent_sha, author)
        new_sha = rs_resp['commit_sha']
        branch_name = rs_resp['branch']
        m_resp = _do_merge2master_commit(git_action,
                                         new_sha,
                                         branch_name,
                                         study_fp,
                                         merged_sha=merged_sha,
                                         prev_file_sha=rs_resp.get('prev_file_sha'))
        new_sha, branch_name, merge_needed = m_resp
    except Exception, e:
        raise GitWorkflowError("Could not remove study #%s! Details: %s" % (study_id, e.message))
    finally:
        git_action.release_lock()
    return {
        "error": 0,
        "branch_name": branch_name,
        "description": "Deleted study #%s" % study_id,
        "sha":  new_sha,
        "merge_needed": merge_needed,
    }

def merge_from_master(git_action, study_id, auth_info, parent_sha):
    """merge from master into the WIP for this study/author
    this is needed to allow a worker's future saves to
    be merged seamlessly into master
    """
    gh_user, author = get_user_author(auth_info)
    acquire_lock_raise(git_action, fail_msg="Could not acquire lock to merge study #{s}".format(s=study_id))
    try:
        git_action.checkout_master()
        written_fp = git_action.path_for_study(study_id)
        if os.path.exists(written_fp):
            master_file_blob_sha = git_action.get_blob_sha_for_file(written_fp)
        else:
            raise GitWorkflowError('Study "{}" does not exist on master'.format(study_id))
        branch = git_action.create_or_checkout_branch(gh_user, study_id, parent_sha)
        new_sha = git_action.merge('master', branch)
    finally:
        git_action.release_lock()
    # What other useful information should be returned on a successful write?
    return {
        "error": 0,
        "resource_id": study_id,
        "branch_name": branch,
        "description": "Updated study #%s" % study_id,
        "sha":  new_sha,
        "merged_sha": master_file_blob_sha,
    }
