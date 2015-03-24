#!/usr/bin/env python
from peyotl.utility.str_util import is_str_type
from peyotl.nexson_syntax import write_as_json
from peyotl.utility import get_logger
import tempfile #@TEMPORARY for deprecated write_study
import shutil
from sh import git
import sh
import re
import os
from peyotl.git_storage import GitActionBase
from peyotl.git_storage.git_action import get_HEAD_SHA1, \
                                          get_user_author

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

#TODO: keep this?
def get_filepath_for_simple_id(repo_dir, study_id):
    return '{r}/study/{s}/{s}.json'.format(r=repo_dir, s=study_id)

class GitAction(GitActionBase):
    def __init__(self,
                 repo,
                 remote=None,
                 git_ssh=None,
                 pkey=None,
                 cache=None, #pylint: disable=W0613
                 path_for_study_fn=None,
                 max_file_size=None):
        """Create a GitAction object to interact with a Git repository

        Example:
        gd   = GitAction(repo="/home/user/git/foo")

        Note that this requires write access to the
        git repository directory, so it can create a
        lockfile in the .git directory.

        """
        GitActionBase.__init__(self,
                               repo,
                               remote,
                               git_ssh,
                               pkey,
                               cache,
                               path_for_study_fn,
                               max_file_size,
                               path_for_doc_id_fn=get_filepath_for_namespaced_id)
    @property
    def path_for_study(self):
        return self.path_for_doc
    @property
    def return_study(self):
        return self.return_doc

    #TODO:type-specific
    def get_changed_studies(self, ancestral_commit_sha, study_ids_to_check=None):
        '''Returns the set of studies that have changed on the master since
        commit `ancestral_commit_sha` or `False` (on an error)

        if `study_ids_to_check` is passed in, it should be an iterable list of
            IDs. Only IDs in this list will be returned.
        '''
        try:
            x = git(self.gitdir,
                    self.gitwd,
                    "diff-tree",
                    "--name-only",
                    "-r",
                    ancestral_commit_sha,
                    "master")
        except:
            _LOG.exception('diff-tree failed')
            return False
        touched = set()
        for f in x.split('\n'):
            if f.startswith('study/'):
                try:
                    study_id = f.split('/')[-2]
                    touched.add(study_id)
                except:
                    pass
        if study_ids_to_check:
            tc = set(study_ids_to_check)
            return tc.intersection(touched)
        return touched

    #TODO:type-specific
    def find_WIP_branches(self, study_id):
        pat = re.compile(r'.*_study_{i}_[0-9]+'.format(i=study_id))
        head_shas = git(self.gitdir, self.gitwd, "show-ref", "--heads")
        ret = {}
        #_LOG.debug('find_WIP_branches head_shas = "{}"'.format(head_shas.split('\n')))
        for lin in head_shas.split('\n'):
            try:
                local_branch_split = lin.split(' refs/heads/')
                if len(local_branch_split) == 2:
                    sha, branch = local_branch_split
                    if pat.match(branch) or branch == 'master':
                        ret[branch] = sha
            except:
                raise
        return ret

    #TODO:type-specific
    def create_or_checkout_branch(self, gh_user, study_id, parent_sha, force_branch_name=False):
        if force_branch_name:
            #@TEMP deprecated
            branch = "{ghu}_study_{rid}".format(ghu=gh_user, rid=study_id)
            if not self.branch_exists(branch):
                try:
                    git(self.gitdir, self.gitwd, "branch", branch, parent_sha)
                    _LOG.debug('Created branch "{b}" with parent "{a}"'.format(b=branch, a=parent_sha))
                except:
                    raise ValueError('parent sha not in git repo')
            self.checkout(branch)
            return branch

        frag = "{ghu}_study_{rid}_".format(ghu=gh_user, rid=study_id)
        branch = self._find_head_sha(frag, parent_sha)
        _LOG.debug('Found branch "{b}" for sha "{s}"'.format(b=branch, s=parent_sha))
        if not branch:
            branch = frag + '0'
            i = 1
            while self.branch_exists(branch):
                branch = frag + str(i)
                i += 1
            _LOG.debug('lowest non existing branch =' + branch)
            try:
                git(self.gitdir, self.gitwd, "branch", branch, parent_sha)
                _LOG.debug('Created branch "{b}" with parent "{a}"'.format(b=branch, a=parent_sha))
            except:
                raise ValueError('parent sha not in git repo')
        self.checkout(branch)
        _LOG.debug('Checked out branch "{b}"'.format(b=branch))
        return branch

    #TODO:type-specific
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
        study_filepath = self.path_for_study(study_id)
        study_dir = os.path.split(study_filepath)[0]

        branch = self.create_or_checkout_branch(gh_user, study_id, parent_sha)
        prev_file_sha = None
        if commit_msg is None:
            msg = "Delete Study #%s via OpenTree API" % study_id
        else:
            msg = commit_msg
        if os.path.exists(study_filepath):
            prev_file_sha = self.get_blob_sha_for_file(study_filepath)
            git(self.gitdir, self.gitwd, "rm", "-rf", study_dir)
            git(self.gitdir,
                self.gitwd,
                "commit",
                author=author,
                message=msg)
        new_sha = git(self.gitdir, self.gitwd, "rev-parse", "HEAD").strip()
        return {'commit_sha': new_sha,
                'branch': branch,
                'prev_file_sha': prev_file_sha,
               }

    #TODO:type-specific
    def write_study(self, study_id, file_content, branch, author):
        """Given a study_id, temporary filename of content, branch and auth_info

        Deprecated but needed until we merge api local-dep to master...

        """
        parent_sha = None
        gh_user = branch.split('_study_')[0]
        fc = tempfile.NamedTemporaryFile()
        if is_str_type(file_content):
            fc.write(file_content)
        else:
            write_as_json(file_content, fc)
        fc.flush()
        try:
            study_filepath = self.path_for_study(study_id)
            study_dir = os.path.split(study_filepath)[0]
            if parent_sha is None:
                self.checkout_master()
                parent_sha = self.get_master_sha()
            branch = self.create_or_checkout_branch(gh_user, study_id, parent_sha, force_branch_name=True)
            # create a study directory if this is a new study EJM- what if it isn't?
            if not os.path.isdir(study_dir):
                os.makedirs(study_dir)
            shutil.copy(fc.name, study_filepath)
            git(self.gitdir, self.gitwd, "add", study_filepath)
            try:
                git(self.gitdir,
                    self.gitwd,
                    "commit",
                    author=author,
                    message="Update Study #%s via OpenTree API" % study_id)
            except Exception as e:
                # We can ignore this if no changes are new,
                # otherwise raise a 400
                if "nothing to commit" in e.message:#@EJM is this dangerous?
                    pass
                else:
                    _LOG.exception('"git commit" failed')
                    self.reset_hard()
                    raise
            new_sha = git(self.gitdir, self.gitwd, "rev-parse", "HEAD")
        except Exception as e:
            _LOG.exception('write_study exception')
            raise GitWorkflowError("Could not write to study #%s ! Details: \n%s" % (study_id, e.message))
        finally:
            fc.close()
        return new_sha

    #TODO:type-specific
    def write_study_from_tmpfile(self, study_id, tmpfi, parent_sha, auth_info, commit_msg=''):
        """Given a study_id, temporary filename of content, branch and auth_info
        """
        gh_user, author = get_user_author(auth_info)
        study_filepath = self.path_for_study(study_id)
        study_dir = os.path.split(study_filepath)[0]
        if parent_sha is None:
            self.checkout_master()
            parent_sha = self.get_master_sha()
        branch = self.create_or_checkout_branch(gh_user, study_id, parent_sha)

        # build complete commit message
        if commit_msg:
            commit_msg = "%s\n\n(Update Study #%s via OpenTree API)" % (commit_msg, study_id)
        else:
            commit_msg = "Update Study #%s via OpenTree API" % study_id
        # create a study directory if this is a new study EJM- what if it isn't?
        if not os.path.isdir(study_dir):
            os.makedirs(study_dir)

        if os.path.exists(study_filepath):
            prev_file_sha = self.get_blob_sha_for_file(study_filepath)
        else:
            prev_file_sha = None
        shutil.copy(tmpfi.name, study_filepath)
        self._add_and_commit(study_filepath, author, commit_msg)
        new_sha = git(self.gitdir, self.gitwd, "rev-parse", "HEAD")
        _LOG.debug('Committed study "{i}" to branch "{b}" commit SHA: "{s}"'.format(i=study_id,
                                                                                    b=branch,
                                                                                    s=new_sha.strip()))
        return {'commit_sha': new_sha.strip(),
                'branch': branch,
                'prev_file_sha': prev_file_sha,
               }



