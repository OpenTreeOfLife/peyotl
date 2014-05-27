#! /usr/bin/env python

##############################################################################
##
##  Adapted from: DendroPy Phylogenetic Computing Library.
##
##  Copyright 2010 Jeet Sukumaran and Mark T. Holder.
##  All rights reserved.
##
##  Sukumaran, J. and M. T. Holder. 2010. DendroPy: a Python library
##     for phylogenetic computing. Bioinformatics 26: 1569-1571.
##
##############################################################################

"""
Support for coverage analysis.
"""

from peyotl.utility import get_logger
import unittest
import shutil
import os

_LOG = get_logger(__name__)

PEYOTL_COVERAGE_ANALYSIS_AVAILABLE = False
try:
    from setuptools import Command
except ImportError:
    _LOG.warn("setuptools.Command could not be imported: setuptools extensions not available")
else:
    try:
        import coverage
    except ImportError:
        _LOG.warn("coverage could not be imported: test coverage analysis not available")
    else:
        _LOG.info("coverage imported successfully: test coverage analysis available")
        PEYOTL_COVERAGE_ANALYSIS_AVAILABLE = True

        from peyotl.test import get_test_suite
        from peyotl.test.support import pathmap

        class CoverageAnalysis(Command):
            """
            Code coverage analysis command.
            """

            description = "run test coverage analysis"
            user_options = [
                ('erase', None, "remove all existing coverage results"),
                ('branch', 'b', 'measure branch coverage in addition to statement coverage'),
                ('test-module=', 't', "explicitly specify a module to test (e.g. 'peyotl.test.test_containers')"),
                ('no-annotate', None, "do not create annotated source code files"),
                ('no-html', None, "do not create HTML report files"),
            ]

            def initialize_options(self):
                """
                Initialize options to default values.
                """
                self.test_module = None
                self.branch = False
                self.erase = False
                self.no_annotate = False
                self.no_html = False
                self.omit = []
                p = os.path.join('peyotl', 'test')
                for triple in os.walk(p):
                    root, files = triple[0], triple[2]
                    for fn in files:
                        if fn.endswith('.py'):
                            fp = os.path.join(root, fn)
                            self.omit.append(fp)
                self.omit.append('*site-packages*')

            def finalize_options(self):
                pass

            def run(self):
                """
                Main command implementation.
                """

                if self.erase:
                    _LOG.warn("removing coverage results directory: %s", pathmap.TESTS_COVERAGE_DIR)
                    try:
                        shutil.rmtree(pathmap.TESTS_COVERAGE_DIR)
                    except:
                        pass
                else:
                    _LOG.info("running coverage analysis ...")
                    if self.test_module is None:
                        test_suite = get_test_suite()
                    else:
                        test_suite = get_test_suite([self.test_module])
                    runner = unittest.TextTestRunner()
                    cov = coverage.coverage(branch=self.branch)
                    cov.start()
                    runner.run(test_suite)
                    cov.stop()
                    if not self.no_annotate:
                        cov.annotate(omit=self.omit,
                                directory=pathmap.TESTS_COVERAGE_SOURCE_DIR)
                    if not self.no_html:
                        cov.html_report(omit=self.omit,
                                directory=pathmap.TESTS_COVERAGE_REPORT_DIR)
                    cov.report(omit=self.omit)
