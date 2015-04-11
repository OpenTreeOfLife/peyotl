'''Generic workflows (combinations of git actions) used as opentree git porcelain
'''
from sh import git
from locket import LockError
import tempfile
from peyotl.utility.str_util import is_str_type
from peyotl.utility import get_logger
import traceback
import json
import os
from peyotl.git_storage.git_action import MergeException, \
                                          get_user_author, \
                                          GitWorkflowError
from peyotl.nexson_syntax import write_as_json


_LOG = get_logger(__name__)

TRACE_FILES = False

def acquire_lock_raise(git_action, fail_msg=''):
    '''Adapts LockError to HTTP. If an exception is not thrown, the git_action has the lock (and must release it!)
    '''
    try:
        git_action.acquire_lock()
    except LockError as e:
        msg = '{o} Details: {d}'.format(o=fail_msg, d=e.message)
        _LOG.debug(msg)
        raise GitWorkflowError(msg)

class GitWorkflowBase(object):
    def __init__(self):
        pass

def _pull_gh(git_action, remote, branch_name):#
    try:
        git_env = git_action.env()
        # TIMING = api_utils.log_time_diff(_LOG, 'lock acquisition', TIMING)
        git(git_action.gitdir, "fetch", remote, _env=git_env)
        git(git_action.gitdir, git_action.gitwd, "merge", remote + '/' + branch_name, _env=git_env)
        _LOG.debug('performed a git pull from branch "{b}" of "{r}" in "{d}"'.format(r=remote,
                                                                                     b=branch_name,
                                                                                     d=git_action.gitwd))
        # TIMING = api_utils.log_time_diff(_LOG, 'git pull', TIMING)
    except Exception as e:
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
                            doc_filepath,
                            merged_sha,
                            prev_file_sha):
    merge_needed = False
    git_action.checkout_master()
    if os.path.exists(doc_filepath):
        b = git_action.get_blob_sha_for_file(doc_filepath)
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

def delete_document(git_action, 
                    doc_id, 
                    auth_info, 
                    parent_sha, 
                    commit_msg=None, 
                    merged_sha=None,
                    doctype_display_name="document"): #pylint: disable=W0613
    author = "{} <{}>".format(auth_info['name'], auth_info['email'])
    gh_user = auth_info['login']
    acquire_lock_raise(git_action, 
                       fail_msg="Could not acquire lock to delete %s #%s" % (doctype_display_name, doc_id))
    try:
        doc_fp = git_action.path_for_doc(doc_id)
        rs_resp = git_action._remove_document(gh_user, doc_id, parent_sha, author, commit_msg=commit_msg)
        new_sha = rs_resp['commit_sha']
        branch_name = rs_resp['branch']
        m_resp = _do_merge2master_commit(git_action,
                                         new_sha,
                                         branch_name,
                                         doc_fp,
                                         merged_sha=merged_sha,
                                         prev_file_sha=rs_resp.get('prev_file_sha'))
        new_sha, branch_name, merge_needed = m_resp
    except Exception as e:
        raise GitWorkflowError("Could not remove %s #%s! Details: %s" % (doctype_display_name, doc_id, e.message))
    finally:
        git_action.release_lock()
    return {
        "error": 0,
        "branch_name": branch_name,
        "description": "Deleted %s #%s" % (doctype_display_name, doc_id),
        "sha":  new_sha,
        "merge_needed": merge_needed,
    }

def merge_from_master(git_action, doc_id, auth_info, parent_sha, doctype_display_name="document" ):
    """merge from master into the WIP for this document/author
    this is needed to allow a worker's future saves to
    be merged seamlessly into master
    """
    gh_user = get_user_author(auth_info)[0]
    acquire_lock_raise(git_action, 
                       fail_msg="Could not acquire lock to merge %s #%s" % (doctype_display_name, doc_id))
    try:
        git_action.checkout_master()
        written_fp = git_action.path_for_doc(doc_id)
        if os.path.exists(written_fp):
            master_file_blob_sha = git_action.get_blob_sha_for_file(written_fp)
        else:
            raise GitWorkflowError('{t} "{i}" does not exist on master'.format(t=doctype_display_name, i=doc_id))
        branch = git_action.create_or_checkout_branch(gh_user, doc_id, parent_sha)
        new_sha = git_action.merge('master', branch)
    finally:
        git_action.release_lock()
    # What other useful information should be returned on a successful write?
    return {
        "error": 0,
        "resource_id": doc_id,
        "branch_name": branch,
        "description": "Updated %s #%s" % (doctype_display_name, doc_id),
        "sha":  new_sha,
        "merged_sha": master_file_blob_sha,
    }

def generic_commit_and_try_merge2master_wf(git_action,
                                          file_content,
                                          doc_id,
                                          auth_info,
                                          parent_sha,
                                          commit_msg='',
                                          merged_sha=None,
                                          doctype_display_name="document"):
    """Actually make a local Git commit and push it to our remote
    """
    #_LOG.debug('generic_commit_and_try_merge2master_wf: doc_id="{s}" \
    #            parent_sha="{p}" merged_sha="{m}"'.format(
    #            s=doc_id, p=parent_sha, m=merged_sha))
    merge_needed = False
    fc = tempfile.NamedTemporaryFile()
    # N.B. we currently assume file_content is text/JSON, or should be serialized from a dict
    try:
        if is_str_type(file_content):
            fc.write(file_content)
        else:
            write_as_json(file_content, fc)
        fc.flush()
        try:
            max_file_size = git_action.max_file_size
        except:
            max_file_size = None
        if max_file_size is not None:
            file_size = os.stat(fc.name).st_size
            if file_size > max_file_size:
                m = 'Commit of {t} "{i}" had a file size ({a} bytes) which exceeds the maximum size allowed ({b} bytes).'
                m = m.format(t=doctype_display_name, i=doc_id, a=file_size, b=max_file_size)
                raise GitWorkflowError(m)
        f = "Could not acquire lock to write to %s #%s" % (doctype_display_name, doc_id)
        acquire_lock_raise(git_action, fail_msg=f)
        try:
            try:
                commit_resp = git_action.write_doc_from_tmpfile(doc_id, fc, parent_sha, auth_info, commit_msg, doctype_display_name)
            except Exception as e:
                _LOG.exception('write_doc_from_tmpfile exception')
                raise GitWorkflowError("Could not write to %s #%s ! Details: \n%s" % 
                                       (doctype_display_name, doc_id, e.message))
            written_fp = git_action.path_for_doc(doc_id)
            branch_name = commit_resp['branch']
            new_sha = commit_resp['commit_sha']
            _LOG.debug('write of {t} {i} on parent {p} returned = {c}'.format(t=doctype_display_name,
                                                                              i=doc_id,
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
        "resource_id": doc_id,
        "branch_name": branch_name,
        "description": "Updated %s #%s" % (doctype_display_name, doc_id),
        "sha":  new_sha,
        "merge_needed": merge_needed,
    }
    _LOG.debug('returning {r}'.format(r=str(r)))
    return r

