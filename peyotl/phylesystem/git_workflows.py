#!/usr/bin/env python
"""Combinations of git actions used as the opentree git porcelain
"""
from peyotl.nexson_syntax import write_as_json
from peyotl.nexson_validation import ot_validate
from peyotl.nexson_syntax import convert_nexson_format
from peyotl.git_storage.git_workflow import (delete_document,
                                             generic_commit_and_try_merge2master_wf,
                                             merge_from_master as _merge_from_master)
from peyotl.git_storage.git_action import GitWorkflowError
from peyotl.utility import get_logger
import traceback
import json
import os

_LOG = get_logger(__name__)

TRACE_FILES = False


def _write_to_next_free(tag, blob):
    """#WARNING not thread safe just a easy of debugging routine!"""
    ind = 0
    pref = '/tmp/peyotl-' + tag + str(ind)
    while os.path.exists(pref):
        ind += 1
        pref = '/tmp/peyotl-' + tag + str(ind)
    write_as_json(blob, pref)


def validate_and_convert_nexson(nexson, output_version, allow_invalid, **kwargs):
    """Runs the nexson validator and returns a converted 4 object:
        nexson, annotation, validation_log, nexson_adaptor

    `nexson` is the nexson dict.
    `output_version` is the version of nexson syntax to be used after validation.
    if `allow_invalid` is False, and the nexson validation has errors, then
        a GitWorkflowError will be generated before conversion.
    """
    try:
        if TRACE_FILES:
            _write_to_next_free('input', nexson)
        annotation, validation_log, nexson_adaptor = ot_validate(nexson, **kwargs)
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


def commit_and_try_merge2master(git_action,
                                file_content,
                                study_id,
                                auth_info,
                                parent_sha,
                                commit_msg='',
                                merged_sha=None):
    """Actually make a local Git commit and push it to our remote
    """
    return generic_commit_and_try_merge2master_wf(git_action,
                                                  file_content,
                                                  doc_id=study_id,
                                                  auth_info=auth_info,
                                                  parent_sha=parent_sha,
                                                  commit_msg=commit_msg,
                                                  merged_sha=merged_sha,
                                                  doctype_display_name="study")


def delete_study(git_action,
                 study_id,
                 auth_info,
                 parent_sha,
                 commit_msg=None,
                 merged_sha=None):  # pylint: disable=W0613
    return delete_document(git_action,
                           study_id,
                           auth_info,
                           parent_sha,
                           commit_msg,
                           merged_sha,
                           doctype_display_name="study")


def merge_from_master(git_action, study_id, auth_info, parent_sha):
    """merge from master into the WIP for this study/author
    this is needed to allow a worker's future saves to
    be merged seamlessly into master
    """
    return _merge_from_master(git_action,
                              doc_id=study_id,
                              auth_info=auth_info,
                              parent_sha=parent_sha,
                              doctype_display_name="study")
