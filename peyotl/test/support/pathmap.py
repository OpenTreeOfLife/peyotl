#! /usr/bin/env python

##############################################################################
##  Based on DendroPy Phylogenetic Computing Library.
##
##  Copyright 2010 Jeet Sukumaran and Mark T. Holder.
##  All rights reserved.
##
##  See "LICENSE.txt" for terms and conditions of usage.
##
##  If you use this work or any portion thereof in published work,
##  please cite it as:
##
##     Sukumaran, J. and M. T. Holder. 2010. DendroPy: a Python library
##     for phylogenetic computing. Bioinformatics 26: 1569-1571.
##
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
    TESTS_DIR = pkg_resources.resource_filename("peyotl", "test")
    SCRIPTS_DIR = pkg_resources.resource_filename("peyotl", os.path.join(os.pardir, "scripts"))
    #_LOG.debug("using pkg_resources path mapping")
except:
    LOCAL_DIR = os.path.dirname(__file__)
    TESTS_DIR = os.path.join(LOCAL_DIR, os.path.pardir)
    PACKAGE_DIR = os.path.join(TESTS_DIR, os.path.pardir)
    SCRIPTS_DIR = os.path.join(PACKAGE_DIR, os.path.pardir, "scripts")
    #_LOG.debug("using local filesystem path mapping")

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
    return get_domains_obj() #We may need to point this at dev instances in some cases.

def get_test_repos():
    return {'mini_phyl': os.path.join(TEST_PHYLESYSTEM_PAR, 'mini_phyl'),
            'mini_system': os.path.join(TEST_PHYLESYSTEM_PAR, 'mini_system'),
    }

def get_test_phylesystem_mirror_parent():
    return TEST_PHYLESYSTEM_MIRROR_PAR

def get_test_phylesystem_mirror_info():
    return {'push': {'parent_dir': get_test_phylesystem_mirror_parent()}}

def get_test_phylesystem():
    from peyotl.phylesystem import _Phylesystem
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
    '''Returns a dict that is the deserialized nexson object
    'filename' should be the fragment of the filepath below
    the nexson test dir.
    '''
    with nexson_file_obj(filename) as fo:
        fc = fo.read()
        return anyjson.loads(fc)

def nexson_file_obj(filename):
    ''' Returns file object.
    'filename' should be the fragment of the filepath below
    the nexson test dir.
    '''
    fp = nexson_source_path(filename=filename)
    return codecs.open(fp, mode='rU', encoding='utf-8')

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
    '''Not thread safe.
    '''
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
