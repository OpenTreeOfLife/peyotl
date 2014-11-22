---
layout: page
title: Testing
permalink: /testing/
---

`peyotl` has a decent, though certainly not comprehensive test suite. To run it:

    $ python setup.py test

will invoke python unittest, and running:

    $ sh maintainer-test.sh

will run these test and some shell-based tests of interest to some developers.

You will seem some tests skipped because of lack of mini_system or mini_phyl. This
is normal. Mark and Emily Jane have some unittests of git interactions that require
privileged access to a particular testing repository. Tests involving this repo
should be skipped.

Running

    $ sh check.sh

runs the `test.sh` script and runs pylint with MTH's preferred configuration (in `dev/pylintrc`)

### Roundtrip tests

A test of the available format conversions (without NeXML validation) can be run with:

    $ sh peyotl/test/check_nexson_nexml_clique.sh peyotl/test/data/nexson/otu.json scripts/nexson/nexson_nexml.py

If you alias your nexml validation tool to the name "validate-nexml" then you can 
run the check_nexml_roundrip.sh and check_nexson_roundrip.sh

Other dependencies for these test scripts are xmllint and saxon-xslt. Note
that these are *not* dependencies for normal usage of 

*Caveat*: check_nexml_roundrip.sh will fail if the attribute order differs from the order used by nexson_nexml.py

## validate-nexml command.
MTH's validate-nexml is shell script:

    #!/bin/sh
    java -jar "${NEXML_PARENT}/xml-validator-read-only/target/xml-validator-1.0-SNAPSHOT-jar-with-dependencies.jar" -s "${NEXML_PARENT}/nexml/xsd/nexml.xsd" $@

where xml-validator-read-only is from http://code.google.com/p/xml-validator/source/checkout
and nexml is a clone of https://github.com/nexml/nexml

You can tweak this by deciding on your NEXML_PARENT dir and running:

    $ cd "${NEXML_PARENT}"
    $ svn checkout http://xml-validator.googlecode.com/svn/trunk/ xml-validator-read-only
    $ git clone https://github.com/nexml/nexml.git
    $ cd xml-validator-read-only
    $ mvn package

## Maintainer tests

There are notes for more extensive tests at the [maintainer](../maintainer) page.

