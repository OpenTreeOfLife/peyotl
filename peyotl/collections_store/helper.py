from peyotl.utility import get_logger
from peyotl.phylesystem.helper import _get_phylesystem_parent
import os
from threading import Lock

_LOG = get_logger(__name__)
_study_index_lock = Lock()


def get_repos(par_list=None, **kwargs):
    """Returns a dictionary of name -> filepath
    `name` is the repo name based on the dir name (not the get repo). It is not
        terribly useful, but it is nice to have so that any mirrored repo directory can
        use the same naming convention.
    `filepath` will be the full path to the repo directory (it will end in `name`)
    """
    _repos = {}  # key is repo name, value repo location
    if par_list is None:
        par_list = _get_phylesystem_parent(**kwargs)
    elif not isinstance(par_list, list):
        par_list = [par_list]
    for p in par_list:
        if not os.path.isdir(p):
            raise ValueError('Docstore parent "{p}" is not a directory'.format(p=p))
        for name in os.listdir(p):
            # TODO: Add an option to filter just phylesystem repos (or any specified type?) here!
            #  - add optional list arg `allowed_repo_names`?
            #  - let the FailedShardCreationError work harmlessly?
            #  - treat this function as truly for phylesystem only?
            if os.path.isdir(os.path.join(p, name + '/.git')):
                _repos[name] = os.path.abspath(os.path.join(p, name))
    if len(_repos) == 0:
        raise ValueError('No git repos in {parent}'.format(parent=str(par_list)))
    return _repos
