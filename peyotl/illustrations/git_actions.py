#!/usr/bin/env python
from peyotl.utility import get_logger
import re
from peyotl.git_storage import GitActionBase

# extract an illustration id from a git repo path (as returned by git-tree)

_LOG = get_logger(__name__)
class MergeException(Exception):
    pass

def get_filepath_for_id(repo_dir, illustration_id):
    from peyotl.illustrations import ILLUSTRATION_ID_PATTERN
    assert bool(ILLUSTRATION_ID_PATTERN.match(illustration_id))
    return '{r}/illustrations/{s}'.format(r=repo_dir, s=illustration_id)

def illustration_id_from_repo_path(path):
    doc_parent_dir = 'illustrations/'
    if path.startswith(doc_parent_dir):
        try:
            illustration_id = path.split(doc_parent_dir)[1]
            return illustration_id
        except:
            return None

class IllustrationsGitAction(GitActionBase):
    def __init__(self,
                 repo,
                 remote=None,
                 git_ssh=None,
                 pkey=None,
                 cache=None, #pylint: disable=W0613
                 path_for_doc_fn=None,
                 max_file_size=None):
        """GitActionBase subclass to interact with a Git repository

        Example:
        gd   = IllustrationsGitAction(repo="/home/user/git/foo")

        Note that this requires write access to the
        git repository directory, so it can create a
        lockfile in the .git directory.

        """
        GitActionBase.__init__(self,
                               'illustration',
                               repo,
                               remote,
                               git_ssh,
                               pkey,
                               cache,
                               path_for_doc_fn,
                               max_file_size,
                               path_for_doc_id_fn=get_filepath_for_id)

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def path_for_illustration(self):
        return self.path_for_doc
    @property
    def return_illustration(self):
        return self.return_document

    def get_changed_docs(self,
                         ancestral_commit_sha,
                         doc_ids_to_check=None):
        return self._get_changed_docs(ancestral_commit_sha,
                                      doc_id_from_repo_path=illustration_id_from_repo_path,
                                      doc_ids_to_check=doc_ids_to_check)

    def find_WIP_branches(self, illustration_id):
        pat = re.compile(r'.*_illustration_{i}_[0-9]+'.format(i=illustration_id))
        return self._find_WIP_branches(illustration_id, branch_pattern=pat)

    def create_or_checkout_branch(self,
                                  gh_user,
                                  illustration_id,
                                  parent_sha,
                                  force_branch_name=False):
        return self._create_or_checkout_branch(gh_user,
                                               illustration_id,
                                               parent_sha,
                                               branch_name_template="{ghu}_illustration_{rid}",
                                               force_branch_name=force_branch_name)

    def remove_illustration(self, first_arg, sec_arg, third_arg, fourth_arg=None, commit_msg=None):
        """Remove an illustration
        Given a illustration_id, branch and optionally an
        author, remove an illustration on the given branch
        and attribute the commit to author.
        Returns the SHA of the commit on branch.
        """
        if fourth_arg is None:
            illustration_id, branch_name, author = first_arg, sec_arg, third_arg
            gh_user = branch_name.split('_illustration_')[0]
            parent_sha = self.get_master_sha()
        else:
            gh_user, illustration_id, parent_sha, author = first_arg, sec_arg, third_arg, fourth_arg
        if commit_msg is None:
            commit_msg = "Delete Illustration '%s' via OpenTree API" % illustration_id
        return self._remove_document(gh_user, illustration_id, parent_sha, author, commit_msg)

    def write_illustration(self, illustration_id, file_content, branch, author):
        """Given an illustration_id, temporary filename of content, branch and auth_info

        Deprecated but needed until we merge api local-dep to master...

        """
        gh_user = branch.split('_illustration_')[0]
        msg = "Update Illustration '%s' via OpenTree API" % illustration_id
        return self.write_document(gh_user,
                                   illustration_id,
                                   file_content,
                                   branch, author,
                                   commit_msg=msg)

    def write_illustration_from_tmpfile(self, illustration_id, tmpfi, parent_sha, auth_info, commit_msg=''):
        """Given an illustration_id, temporary filename of content, branch and auth_info
        """
        return self.write_doc_from_tmpfile(illustration_id,
                                           tmpfi,
                                           parent_sha,
                                           auth_info,
                                           commit_msg,
                                           doctype_display_name="illustration")

