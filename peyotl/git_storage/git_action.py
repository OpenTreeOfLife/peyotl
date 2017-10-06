"""Base class git action manager (subclasses will accommodate each type)"""
from peyotl.utility.str_util import is_str_type
from peyotl.nexson_syntax import write_as_json
from peyotl.utility import get_logger
import os
# noinspection PyUnresolvedReferences
from sh import git  # pylint: disable=E0611
import shutil
import sh
import locket
import codecs
import zipfile
import tempfile  # @TEMPORARY for deprecated write_study

_LOG = get_logger(__name__)


def get_HEAD_SHA1(git_dir):
    """Not locked!
    """
    head_file = os.path.join(git_dir, 'HEAD')
    with open(head_file, 'r') as hf:
        head_contents = hf.read().strip()
    assert head_contents.startswith('ref: ')
    ref_filename = head_contents[5:]  # strip off "ref: "
    real_ref = os.path.join(git_dir, ref_filename)
    with open(real_ref, 'r') as rf:
        return rf.read().strip()


def get_user_author(auth_info):
    """Return commit author info from a dict. Returns username and author string.

    auth_info should have 3 strings:
        `login` (a github log in)
        `name`
        `email`
    username will be in the `login` value. It is used for WIP branch naming.
    the author string will be the name and email joined. This is used in commit messages.
    """
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
                 doc_type,
                 repo,
                 remote=None,
                 git_ssh=None,
                 pkey=None,
                 cache=None,  # pylint: disable=W0613
                 path_for_doc_fn=None,
                 max_file_size=None,
                 path_for_doc_id_fn=None):
        self.repo = repo
        self.doc_type = doc_type
        self.git_dir = os.path.join(repo, '.git')
        self._lock_file = os.path.join(self.git_dir, "API_WRITE_LOCK")
        self._lock_timeout = 30  # in seconds
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
        else:  # EJM needs a test?
            raise ValueError('Repo "{repo}" is not a git repo'.format(repo=self.repo))

    # some methods are required, but particular to each subclass
    def find_WIP_branches(self, some_id):  # pylint: disable=W0613
        raise NotImplementedError("Subclass must implement find_WIP_branches!")

    def create_or_checkout_branch(self,
                                  gh_user,
                                  some_id,
                                  parent_sha,
                                  force_branch_name=False):  # pylint: disable=W0613
        raise NotImplementedError("Subclass must implement create_or_checkout_branch!")

    def env(self):  # @TEMP could be ref to a const singleton.
        d = dict(os.environ)
        if self.git_ssh:
            d['GIT_SSH'] = self.git_ssh
        if self.pkey:
            d['PKEY'] = self.pkey
        return d

    def acquire_lock(self):
        """Acquire a lock on the git repository"""
        _LOG.debug('Acquiring lock')
        self._lock.acquire()

    def release_lock(self):
        """Release a lock on the git repository"""
        _LOG.debug('Releasing lock')
        try:
            self._lock.release()
        except:
            _LOG.debug('Exception releasing lock suppressed.')

    def path_for_doc(self, doc_id):
        """Returns doc_dir and doc_filepath for doc_id.
        """
        full_path = self.path_for_doc_fn(self.repo, doc_id)
        # _LOG.debug('>>>>>>>>>> GitActionBase.path_for_doc_fn: {}'.format(self.path_for_doc_fn))
        # _LOG.debug('>>>>>>>>>> GitActionBase.path_for_doc returning: [{}]'.format(full_path))
        return full_path

    def lock(self):
        """ for syntax:
        with git_action.lock():
            git_action.checkout()
        """
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
        """Return the current branch name"""
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
            # _LOG.debug("lin = '{l}'".format(l=lin))
            if lin.startswith(parent_sha):
                local_branch_split = lin.split(' refs/heads/')
                # _LOG.debug("local_branch_split = '{l}'".format(l=local_branch_split))
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
        """fetch from a remote"""
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
            # _LOG.debug('ls-tree said "{}"'.format(r))
            line = r.strip()
            ls = line.split()
            # _LOG.debug('ls is "{}"'.format(str(ls)))
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
                      '--follow',  # Track file's history when moved/renamed...
                      '--find-renames=100%',  # ... but only if the contents are identical!
                      '--',
                      filepath)
            # _LOG.debug('log said "{}"'.format(log))
            log = log.strip('\n\x1e').split("\x1e")
            log = [row.strip().split("\x1f") for row in log]
            log = [dict(zip(GIT_COMMIT_FIELDS, row)) for row in log]
        except:
            _LOG.exception('git log failed')
            raise
        return log

    def _add_and_commit(self, doc_filepath, author, commit_msg):
        """Low level function used internally when you have an absolute filepath to add and commit"""
        try:
            git(self.gitdir, self.gitwd, "add", doc_filepath)
            git(self.gitdir, self.gitwd, "commit", author=author, message=commit_msg)
        except Exception as e:
            # We can ignore this if no changes are new,
            # otherwise raise a 400
            if "nothing to commit" in e.message:  # @EJM is this dangerous?
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

    def return_document(self, doc_id, branch='master', commit_sha=None, return_WIP_map=False):
        """Return the
            blob[0] contents of the given doc_id,
            blob[1] the SHA1 of the HEAD of branch (or `commit_sha`)
            blob[2] dictionary of WIPs for this doc.
        If the doc_id does not exist, it returns the empty string.
        If `commit_sha` is provided, that will be checked out and returned.
            otherwise the branch will be checked out.
        """
        _LOG.warn('GitActionBase.return_document({s}, {b}, {c}...)'.format(s=doc_id, b=branch, c=commit_sha))
        if commit_sha is None:
            self.checkout(branch)
            head_sha = get_HEAD_SHA1(self.git_dir)
        else:
            self.checkout(commit_sha)
            head_sha = commit_sha
        doc_filepath = self.path_for_doc(doc_id)
        _LOG.warn('GitActionBase.return_document ... doc_filepath: {p}'.format(p=doc_filepath))
        try:
            with codecs.open(doc_filepath, mode='r', encoding='utf-8') as f:
                content = f.read()
        except:
            content = None
        if return_WIP_map:
            d = self.find_WIP_branches(doc_id)
            return content, head_sha, d
        return content, head_sha

    def _get_changed_docs(self,
                          ancestral_commit_sha,
                          doc_id_from_repo_path,
                          doc_ids_to_check=None):
        """Returns the set of documents that have changed on the master since
        commit `ancestral_commit_sha` or `False` (on an error)

        'doc_id_from_repo_path' is a required function

        if `doc_ids_to_check` is passed in, it should be an iterable list of
            IDs. Only IDs in this list will be returned.
        """
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
            found_id = doc_id_from_repo_path(f)
            if found_id:
                touched.add(found_id)

        if doc_ids_to_check:
            tc = set(doc_ids_to_check)
            return tc.intersection(touched)
        return touched

    def _find_WIP_branches(self, doc_id, branch_pattern):
        head_shas = git(self.gitdir, self.gitwd, "show-ref", "--heads")
        ret = {}
        # _LOG.debug('find_WIP_branches head_shas = "{}"'.format(head_shas.split('\n')))
        for lin in head_shas.split('\n'):
            try:
                local_branch_split = lin.split(' refs/heads/')
                if len(local_branch_split) == 2:
                    sha, branch = local_branch_split
                    if branch_pattern.match(branch) or branch == 'master':
                        ret[branch] = sha
            except:
                raise
        return ret

    def _create_or_checkout_branch(self,
                                   gh_user,
                                   doc_id,
                                   parent_sha,
                                   branch_name_template='{ghu}_doc_{rid}',
                                   force_branch_name=False):
        if force_branch_name:
            # @TEMP deprecated
            branch = branch_name_template.format(ghu=gh_user, rid=doc_id)
            if not self.branch_exists(branch):
                try:
                    git(self.gitdir, self.gitwd, "branch", branch, parent_sha)
                    _LOG.debug('Created branch "{b}" with parent "{a}"'.format(b=branch, a=parent_sha))
                except:
                    raise ValueError('parent sha not in git repo')
            self.checkout(branch)
            return branch

        frag = branch_name_template.format(ghu=gh_user, rid=doc_id) + "_"
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
                raise ValueError('parent sha "{a}" not in git repo!'.format(a=parent_sha))
        self.checkout(branch)
        _LOG.debug('Checked out branch "{b}"'.format(b=branch))
        return branch

    def _remove_document(self, gh_user, doc_id, parent_sha, author, commit_msg=None, subresource_path=None):
        """Remove a document
        Remove a document on the given branch and attribute the commit to author.
        Returns the SHA of the commit on branch.
        """
        _LOG.warn("@@@@@@@@ GitActionBase._remove_document, doc_id={}".format(doc_id))
        doc_filepath = self.path_for_doc(doc_id)
        _LOG.warn("@@@@@@@@ GitActionBase._remove_document, doc_filepath={}".format(doc_filepath))
        if subresource_path:
            # ignore the main file, build on the doc's main folder
            doc_folderpath = os.path.dirname(doc_filepath)
            doc_filepath = '{d}/{s}'.format(d=doc_folderpath, s=subresource_path)
            _LOG.warn("@@@@@@@@ GitActionBase._remove_document, full path to subresource = {}".format(doc_filepath))

        branch = self.create_or_checkout_branch(gh_user, doc_id, parent_sha)
        prev_file_sha = None
        if commit_msg is None:
            if subresource_path:
                msg = "Delete subresource '{s}' of document '{i}' via OpenTree API".format(s=subresource_path, i=doc_id)
            else:
                msg = "Delete document '%s' via OpenTree API" % doc_id
        else:
            msg = commit_msg
        if os.path.exists(doc_filepath):
            prev_file_sha = self.get_blob_sha_for_file(doc_filepath)
            if self.doc_type in ('nexson', 'illustration',) and not subresource_path:
                # delete the parent directory entirely
                doc_dir = os.path.split(doc_filepath)[0]
                _LOG.warn("@@@@@@@@ GitActionBase._remove_document, doc_dir={}".format(doc_dir))
                git(self.gitdir, self.gitwd, "rm", "-rf", doc_dir)
            elif subresource_path or self.doc_type in ('collection', 'favorites', 'amendment',):
                # delete just the target file
                _LOG.warn("@@@@@@@@ GitActionBase._remove_document, doc_filepath={}".format(doc_filepath))
                git(self.gitdir, self.gitwd, "rm", doc_filepath)
            else:
                raise NotImplementedError("No deletion rules for doc_type '{}'".format(self.doc_type))
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

    def write_document(self, gh_user, doc_id, file_content, branch, author, commit_msg=None):
        """Given a document id, temporary filename of content, branch and auth_info

        Deprecated but needed until we merge api local-dep to master...

        """
        parent_sha = None
        fc = tempfile.NamedTemporaryFile()
        # N.B. we currently assume file_content is text/JSON, or should be serialized from a dict
        if is_str_type(file_content):
            fc.write(file_content)
        else:
            write_as_json(file_content, fc)
        fc.flush()
        try:
            doc_filepath = self.path_for_doc(doc_id)
            doc_dir = os.path.split(doc_filepath)[0]
            if parent_sha is None:
                self.checkout_master()
                parent_sha = self.get_master_sha()
            branch = self.create_or_checkout_branch(gh_user, doc_id, parent_sha, force_branch_name=True)
            # create a document directory if this is a new doc EJM- what if it isn't?
            if not os.path.isdir(doc_dir):
                os.makedirs(doc_dir)
            shutil.copy(fc.name, doc_filepath)
            git(self.gitdir, self.gitwd, "add", doc_filepath)
            if commit_msg is None:
                commit_msg = "Update document '%s' via OpenTree API" % doc_id
            try:
                git(self.gitdir,
                    self.gitwd,
                    "commit",
                    author=author,
                    message=commit_msg)
            except Exception as e:
                # We can ignore this if no changes are new,
                # otherwise raise a 400
                if "nothing to commit" in e.message:  # @EJM is this dangerous?
                    pass
                else:
                    _LOG.exception('"git commit" failed')
                    self.reset_hard()
                    raise
            new_sha = git(self.gitdir, self.gitwd, "rev-parse", "HEAD")
        except Exception as e:
            _LOG.exception('write_document exception')
            raise GitWorkflowError("Could not write to document #%s ! Details: \n%s" % (doc_id, e.message))
        finally:
            fc.close()
        return new_sha

    def write_doc_from_tmpfile(self,
                               doc_id,
                               tmpfi,
                               parent_sha,
                               auth_info,
                               commit_msg='',
                               doctype_display_name="document",
                               archive=None):
        """Given a doc_id, temporary filename of content, branch and auth_info

        If an archive is provided, the doc is a folderish type with multiple
        files and folders beyond our assumed JSON core file `tmpfi`. In this
        case, we assume that `tmpfi` may have been altered on receipt, e.g.
        updates to its storage metadata, so `tmpfi` should overwrite the
        corresponding file in the archive, if any.
        """
        gh_user, author = get_user_author(auth_info)
        doc_filepath = self.path_for_doc(doc_id)
        doc_dir = os.path.split(doc_filepath)[0]
        if parent_sha is None:
            self.checkout_master()
            parent_sha = self.get_master_sha()
        branch = self.create_or_checkout_branch(gh_user, doc_id, parent_sha)

        # build complete (probably type-specific) commit message
        default_commit_msg = "Update %s '%s' via OpenTree API" % (doctype_display_name, doc_id)
        if commit_msg:
            commit_msg = "%s\n\n(%s)" % (commit_msg, default_commit_msg)
        else:
            commit_msg = default_commit_msg

        # create a doc directory if this is a new document  EJM- what if it isn't?
        if not os.path.isdir(doc_dir):
            os.makedirs(doc_dir)

        if os.path.exists(doc_filepath):
            prev_file_sha = self.get_blob_sha_for_file(doc_filepath)
        else:
            prev_file_sha = None
        if archive:
            # unzip all files and folders into the doc-folder, stage for final commit
            # empty the doc folder completely
            git(self.gitdir, self.gitwd, "rm", "-rf", "'{}/*'".format(doc_dir))
            # extract all archived files into the doc's dir
            try:
                with ZipFile(archive, 'r') as zipped:
                    _LOG.debug('Unpacking ZIP archive for this update...')
                    _LOG.debug(zipped.namelist())
                    zipped.extractall(doc_dir)
            except:
                msg="Failed to extract ZIP archive! it's a <{}>".format(type(archive))
                _LOG.exception(msg)
                raise ValueError(msg)
            # re-add doc's folder to recapture all files for _add_and_commit below
            git(self.gitdir, self.gitwd, "add", doc_dir)
        shutil.copy(tmpfi.name, doc_filepath)
        self._add_and_commit(doc_filepath, author, commit_msg)
        new_sha = git(self.gitdir, self.gitwd, "rev-parse", "HEAD")
        _LOG.debug('Committed document "{i}" to branch "{b}" commit SHA: "{s}"'.format(i=doc_id,
                                                                                       b=branch,
                                                                                       s=new_sha.strip()))
        return {'commit_sha': new_sha.strip(),
                'branch': branch,
                'prev_file_sha': prev_file_sha,
                }
