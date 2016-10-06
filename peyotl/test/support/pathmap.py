#! /usr/bin/env python

##############################################################################
#  Based on DendroPy Phylogenetic Computing Library.
#
#  Copyright 2010 Jeet Sukumaran and Mark T. Holder.
#  All rights reserved.
#
#  See "LICENSE.txt" for terms and conditions of usage.
#
#  If you use this work or any portion thereof in published work,
#  please cite it as:
#
#     Sukumaran, J. and M. T. Holder. 2010. DendroPy: a Python library
#     for phylogenetic computing. Bioinformatics 26: 1569-1571.
#
##############################################################################

"""
Path mapping for various test resources.
"""
from peyotl.utility import pretty_timestamp, get_logger

try:
    import anyjson
except:
    import json


    class Wrapper(object):
        pass


    anyjson = Wrapper()
    anyjson.loads = json.loads
import codecs
import os

_LOG = get_logger(__name__)

try:
    import pkg_resources

    # NOTE that resource_filename can return an absolute or package-relative
    # path, depending on the package/egg type! We'll try to ensure absolute
    # paths in some areas below.
    TESTS_DIR = pkg_resources.resource_filename("peyotl", "test")
    SCRIPTS_DIR = pkg_resources.resource_filename("peyotl", os.path.join(os.pardir, "scripts"))
    _LOG.debug("using pkg_resources path mapping")
except:
    LOCAL_DIR = os.path.dirname(__file__)
    TESTS_DIR = os.path.join(LOCAL_DIR, os.path.pardir)
    PACKAGE_DIR = os.path.join(TESTS_DIR, os.path.pardir)
    SCRIPTS_DIR = os.path.join(PACKAGE_DIR, os.path.pardir, "scripts")
    _LOG.debug("using local filesystem path mapping")

TESTS_DATA_DIR = os.path.join(TESTS_DIR, "data")
TESTS_OUTPUT_DIR = os.path.join(TESTS_DIR, "output")
TESTS_SCRATCH_DIR = os.path.join(TESTS_DIR, "scratch")
TESTS_COVERAGE_DIR = os.path.join(TESTS_DIR, "coverage")
TESTS_COVERAGE_REPORT_DIR = os.path.join(TESTS_COVERAGE_DIR, "report")
TESTS_COVERAGE_SOURCE_DIR = os.path.join(TESTS_COVERAGE_DIR, "source")

TEST_PHYLESYSTEM_PAR = os.path.join(TESTS_DATA_DIR, 'mini_par')
TEST_PHYLESYSTEM_MIRROR_PAR = os.path.join(TEST_PHYLESYSTEM_PAR, 'mirror')
TEST_PHYLESYSTEM_TEMPLATE = os.path.join(TESTS_DATA_DIR, 'template_mini_par')


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


def all_files(prefix):
    d = os.path.join(TESTS_DATA_DIR, prefix)
    s = set()
    for p in os.listdir(d):
        fp = os.path.join(d, p)
        if os.path.isfile(fp):
            s.add(fp)
    return s


def nexson_obj(filename):
    """Returns a dict that is the deserialized nexson object
    'filename' should be the fragment of the filepath below
    the nexson test dir.
    """
    with nexson_file_obj(filename) as fo:
        fc = fo.read()
        return anyjson.loads(fc)


def nexson_file_obj(filename):
    """ Returns file object.
    'filename' should be the fragment of the filepath below
    the nexson test dir.
    """
    fp = nexson_source_path(filename=filename)
    return codecs.open(fp, mode='r', encoding='utf-8')


def shared_test_dir():
    return os.path.join(TESTS_DATA_DIR, "shared-api-tests")


def nexson_source_path(filename=None):
    if filename is None:
        filename = ""
    return os.path.join(TESTS_DATA_DIR, "nexson", filename)


def nexml_source_path(filename=None):
    if filename is None:
        filename = ""
    return os.path.join(TESTS_DATA_DIR, "nexml", filename)


def named_output_stream(filename=None, suffix_timestamp=True):
    return open(named_output_path(filename=filename, suffix_timestamp=suffix_timestamp), "w")


def named_output_path(filename=None, suffix_timestamp=True):
    if filename is None:
        filename = ""
    else:
        if isinstance(filename, list):
            filename = os.path.sep.join(filename)
        if suffix_timestamp:
            filename = "%s.%s" % (filename, pretty_timestamp(style=1))
    if not os.path.exists(TESTS_OUTPUT_DIR):
        os.makedirs(TESTS_OUTPUT_DIR)
    return os.path.join(TESTS_OUTPUT_DIR, filename)


def script_source_path(filename=None):
    if filename is None:
        filename = ""
    return os.path.join(SCRIPTS_DIR, filename)


def next_unique_scratch_filepath(fn):
    frag = os.path.join(TESTS_SCRATCH_DIR, fn)
    if os.path.exists(TESTS_SCRATCH_DIR):
        if not os.path.isdir(TESTS_SCRATCH_DIR):
            mf = 'Cannot create temp file "{f}" because a file "{c}" is in the way'
            msg = mf.format(f=frag, c=TESTS_SCRATCH_DIR)
            raise RuntimeError(msg)
    else:
        os.makedirs(TESTS_SCRATCH_DIR)
    return next_unique_filepath(frag)


def next_unique_filepath(fp):
    """Not thread safe.
    """
    if os.path.exists(fp):
        ind = 0
        while True:
            np = '{f}.{i:d}'.format(f=fp, i=ind)
            if not os.path.exists(np):
                return np
            ind += 1
    return fp


def json_source_path(filename=None):
    if filename is None:
        filename = ""
    return os.path.join(TESTS_DATA_DIR, "json", filename)


def collection_obj(filename):
    """Returns a dict that is the deserialized collection object
    'filename' should be the fragment of the filepath below
    the collection test dir.
    """
    with collection_file_obj(filename) as fo:
        fc = fo.read()
        return anyjson.loads(fc)


def collection_file_obj(filename):
    """ Returns file object.
    'filename' should be the fragment of the filepath below
    the collection test dir.
    """
    fp = collection_source_path(filename=filename)
    return codecs.open(fp, mode='r', encoding='utf-8')


def collection_source_path(filename=None):
    if filename is None:
        filename = ""
    return os.path.join(TESTS_DATA_DIR, "collections", filename)


def amendment_obj(filename):
    """Returns a dict that is the deserialized amendment object
    'filename' should be the fragment of the filepath below
    the amendment test dir.
    """
    with amendment_file_obj(filename) as fo:
        fc = fo.read()
        return anyjson.loads(fc)


def amendment_file_obj(filename):
    """ Returns file object.
    'filename' should be the fragment of the filepath below
    the amendment test dir.
    """
    fp = amendment_source_path(filename=filename)
    return codecs.open(fp, mode='r', encoding='utf-8')


def amendment_source_path(filename=None):
    if filename is None:
        filename = ""
    return os.path.join(TESTS_DATA_DIR, "amendments", filename)
