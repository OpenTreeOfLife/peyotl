#!/usr/bin/env python
from peyotl.utility import get_logger
import re
import os
from peyotl.git_storage import GitActionBase

# extract a study id from a git repo path (as returned by git-tree)

_LOG = get_logger(__name__)


class MergeException(Exception):
    pass


def get_filepath_for_namespaced_id(repo_dir, study_id):
    if len(study_id) < 4:
        while len(study_id) < 2:
            study_id = '0' + study_id
        study_id = 'pg_' + study_id
    elif study_id[2] != '_':
        study_id = 'pg_' + study_id
    from peyotl.phylesystem import STUDY_ID_PATTERN
    assert bool(STUDY_ID_PATTERN.match(study_id))
    frag = study_id[-2:]
    while len(frag) < 2:
        frag = '0' + frag
    dest_topdir = study_id[:3] + frag
    dest_subdir = study_id
    dest_file = dest_subdir + '.json'
    return os.path.join(repo_dir, 'study', dest_topdir, dest_subdir, dest_file)


def get_filepath_for_simple_id(repo_dir, study_id):
    return '{r}/study/{s}/{s}.json'.format(r=repo_dir, s=study_id)


def study_id_from_repo_path(path):
    if path.startswith('study/'):
        try:
            study_id = path.split('/')[-2]
            return study_id
        except:
            return None


class PhylesystemGitAction(GitActionBase):
    def __init__(self,
                 repo,
                 remote=None,
                 git_ssh=None,
                 pkey=None,
                 cache=None,  # pylint: disable=W0613
                 path_for_doc_fn=None,
                 max_file_size=None):
        """Create a GitAction object to interact with a Git repository

        Example:
        gd   = PhylesystemGitAction(repo="/home/user/git/foo")

        Note that this requires write access to the
        git repository directory, so it can create a
        lockfile in the .git directory.

        """
        GitActionBase.__init__(self,
                               'nexson',
                               repo,
                               remote,
                               git_ssh,
                               pkey,
                               cache,
                               path_for_doc_fn,
                               max_file_size,
                               path_for_doc_id_fn=get_filepath_for_namespaced_id)

    # rename some generic members in the base class, for clarity and backward compatibility
    @property
    def path_for_study(self):
        return self.path_for_doc

    @property
    def return_study(self):
        return self.return_document

    def get_changed_docs(self,
                         ancestral_commit_sha,
                         doc_ids_to_check=None):
        return self._get_changed_docs(ancestral_commit_sha,
                                      doc_id_from_repo_path=study_id_from_repo_path,
                                      doc_ids_to_check=doc_ids_to_check)

    def find_WIP_branches(self, study_id):
        pat = re.compile(r'.*_study_{i}_[0-9]+'.format(i=study_id))
        return self._find_WIP_branches(study_id, branch_pattern=pat)

    def create_or_checkout_branch(self,
                                  gh_user,
                                  study_id,
                                  parent_sha,
                                  force_branch_name=False):
        return self._create_or_checkout_branch(gh_user,
                                               study_id,
                                               parent_sha,
                                               branch_name_template="{ghu}_study_{rid}",
                                               force_branch_name=force_branch_name)

    def remove_study(self, first_arg, sec_arg, third_arg, fourth_arg=None, commit_msg=None):
        """Remove a study
        Given a study_id, branch and optionally an
        author, remove a study on the given branch
        and attribute the commit to author.
        Returns the SHA of the commit on branch.
        """
        if fourth_arg is None:
            study_id, branch_name, author = first_arg, sec_arg, third_arg
            gh_user = branch_name.split('_study_')[0]
            parent_sha = self.get_master_sha()
        else:
            gh_user, study_id, parent_sha, author = first_arg, sec_arg, third_arg, fourth_arg
        if commit_msg is None:
            commit_msg = "Delete Study #%s via OpenTree API" % study_id
        return self._remove_document(gh_user, study_id, parent_sha, author, commit_msg)

    def write_study(self, study_id, file_content, branch, author):
        """Given a study_id, temporary filename of content, branch and auth_info

        Deprecated but needed until we merge api local-dep to master...

        """
        gh_user = branch.split('_study_')[0]
        msg = "Update Study #%s via OpenTree API" % study_id
        return self.write_document(gh_user,
                                   study_id,
                                   file_content,
                                   branch,
                                   author,
                                   commit_msg=msg)

    def write_study_from_tmpfile(self, study_id, tmpfi, parent_sha, auth_info, commit_msg=''):
        """Given a study_id, temporary filename of content, branch and auth_info
        """
        return self.write_doc_from_tmpfile(study_id,
                                           tmpfi,
                                           parent_sha,
                                           auth_info,
                                           commit_msg,
                                           doctype_display_name="study")
