#!/usr/bin/env python

# list of the absolute path to the each of the known "study" directories in phylesystem repos.
_study_dirs = []



def _get_phylesystem_parent():
    global _repo_dirs
    if 'PHYLESYSTEM_PARENT' in os.environ:
        phylesystem_parent = os.environ.get('PHYLESYSTEM_PARENT')
    else:
        try:
            from peyotl import config, _expand_path
            phylesystem_parent = _expand_path(config('phylesystem', 'parent'))
        except:
            phylesystem_parent = os.path.abspath(os.curdir)

    x = phylesystem_parent.split(':') #TEMP hardcoded assumption that : does not occur in a path name
    for p in x:
        if not os.path.isdir(p):
            raise ValueError('No phylesystem parent "{p}" is not a directory'.format(p=phylesystem_parent))
    return x

def search_for_study_dirs(parent_list=None):
    if not parent_list:
        parent_list = _get_phylesystem_parent()
    if isinstance(parent_list, str):
        parent_list = [parent_list]
    for p in parent_list:
        _search_for_repo_dirs(p)
    if not _study_dirs:
        raise ValueError('No phylesystem repositories found under "{p}"'.format(p=phylesystem_parent))


def _search_for_repo_dirs(par):
    global _study_dirs
    for n in os.listdir(par):
        if not n.startswith('phylesystem'): #TEMP Hardcode repo name pattern
            continue
        fp =  os.path.join(par, n)
        if os.path.isdir(fp):
            d = os.path.abspath(fp)
            s = os.path.join(d, 'study') #TEMP Hardcode file name pattern
            if os.path.exists(s):
                if s not in _study_dirs:
                    _study_dirs.append(s)

def _iter_phylesystem_repos(study_dir_list=None,
                            parent_list=None):
    global _study_dirs
    if study_dir_list is None:
        if not _study_dirs:
            search_for_study_dirs(parent_list)
        study_dir_list = _study_dirs
    for i in study_dir_list:
        yield i

def phylesystem_studies(study_dir_list=None,
                        parent_list=None):
    '''Generator that allows you to iterate over all detected phylesystem
    studies.
    See documentation about specifying PHYLESYSTEM_PARENT
    '''
    for p in _iter_phylesystem_repos(study_dir_list=study_dir_list,
                                     parent_list=parent_list):
        for c in os.listdir(p):
            sp = os.path.join(p, c)
            if os.path.isdir(sp):
                fp = os.path.join(sp, c + '.json') #TEMP Hardcode file name pattern
                if os.path.isfile(fp):
                    yield fp
