#!/usr/bin/env python
# -*- coding: utf-8 -*-
from peyutil.test import PathMapForTests
import os
from peyotl import get_logger

_LOG = get_logger(__name__)

def get_test_path_mapper():
    return PathMapForTests(path_map_filepath=__file__)

def get_test_ot_service_domains():
    from peyotl.api.wrapper import get_domains_obj
    return get_domains_obj()  # We may need to point this at dev instances in some cases.


def get_test_repos(requested=None):
    """Returns a dict mapping a nicknam (mini_.*) to the full path to that
    testing repository, if that testing repository is an existing directory.

    Empty dict if peyotl is not set up for testing"""
    repo_parent_path = TEST_PHYLESYSTEM_PAR
    _LOG.warn("TESTING repo_parent_path:{}".format(repo_parent_path))
    # NOTE that we want absolute filesystem paths for repos, so that downstream git
    # actions can always find their target files regardless of --work-tree
    # setting (which dictates the working directory for git ops)
    if not os.path.isabs(repo_parent_path):
        repo_parent_path = os.path.abspath(repo_parent_path)
        _LOG.warn("ABSOLUTE repo_parent_path:{}".format(repo_parent_path))
    poss = {'mini_phyl': os.path.join(repo_parent_path, 'mini_phyl'),
            'mini_system': os.path.join(repo_parent_path, 'mini_system'),
            'mini_collections': os.path.join(repo_parent_path, 'mini_collections'),
            'mini_amendments': os.path.join(repo_parent_path, 'mini_amendments'),
            }
    if requested is not None:
        try:
            poss = {k: poss[k] for k in requested}
        except KeyError:
            return {}
    return {k: v for k, v in poss.items() if os.path.isdir(v)}

TESTS_DATA_DIR = get_test_path_mapper().tests_data_dir
TEST_PHYLESYSTEM_PAR = os.path.join(TESTS_DATA_DIR, 'mini_par')
TEST_PHYLESYSTEM_MIRROR_PAR = os.path.join(TEST_PHYLESYSTEM_PAR, 'mirror')
TEST_PHYLESYSTEM_TEMPLATE = os.path.join(TESTS_DATA_DIR, 'template_mini_par')

def get_test_phylesystem_mirror_parent():
    return TEST_PHYLESYSTEM_MIRROR_PAR


def get_test_phylesystem_mirror_info():
    return {'push': {'parent_dir': get_test_phylesystem_mirror_parent()}}


def get_test_phylesystem():
    from peyotl.phylesystem.phylesystem_umbrella import _Phylesystem
    r = get_test_repos()
    mi = get_test_phylesystem_mirror_info()
    mi['push']['remote_map'] = {'GitHubRemote': 'git@github.com:mtholder'}
    return _Phylesystem(repos_dict=r, mirror_info=mi)


