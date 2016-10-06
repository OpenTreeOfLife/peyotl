---
layout: page
title: Maintainer
permalink: /maintainer/
---

## Tests and pylint
Running

    $ sh tests/check.sh

runs the `test.sh` script and runs pylint with MTH's preferred configuration (in `dev/pylintrc`)

## maintainer-tests
A few of the tests in the peyotl test suite (including some
tiggered by the `maintainer-test.sh` but not by `python setup.py test`).
require more setup than we expect a typical user to want to do.
In particular, you need some phylesystem-style repos on which you can
perform git actions - including pushes to remotes.

    $ bash tests/maintainer-tests.sh

invokes the richer test suite. However, these tests require some set up.

The tests of logging require that you do not have a `~/.peyotl/config` file. 
See the [configuration page](../configuration) for details on how to use environmental
variables instead of the default config file location.

### tests requiring local clones of mini testing repos
Running

    $ bash bootstrap.sh

should clone the testing repos that you need to run tests on the phyleystem, amendments,
and collections tests.

If you do not run that command, 
you will seem some tests skipped because of lack of `mini_system` or `mini_phyl`
`mini_amendments` and `mini_collections`. 
Skipping these tests is normal
is normal. Mark and Emily Jane have some unittests of git interactions that require
privileged access to a particular testing repository. 


If you are interested in running these "maintainer" tests you can run 'bootstrap.sh'
file at the top of the peyotl repo. Or you can do the setup manually by:

    1. fork https://github.com/mtholder/mini_phyl and
       https://github.com/mtholder/mini_system on github (or some other
       server on which you have write permissions).

    2. From the top of the phylesystem repo directory:
    
    mkdir peyotl/test/data/mini_par
    cd peyotl/test/data/mini_par

    3. Used `git clone ...` to create clones of mini_phyl and mini_system
        in this directory.

At that point you should not see tests in the peyotl being skipped
with messages that refer to Peyotl not being configured for maintainer tests.

If you have not checked out these testing repos with the git protocol
then the push-to-mirror operations will not be tested.

## Testing wrappers of web-services

Put `RUN_WEB_SERVICE_TESTS` in your environment if you want the 
tests that call open tree of life web services to run.
Without this variable, those tests are skipped.

## Some tricks 
These are probably mainly of interest to people who develop `peyotl`

### curl calls for web-services
When debugging or writing issues, it is nice to have a curl version of a web service
call. If `PEYOTL_CURL_LOG_FILE` is in the env when peyotl is executing, the api
wrappers will write a curl version of their activity to the filepath indicated by that
variable. These files get big, so you probably don't want to have this on by default.
MTH adds the following 3 functions to bash when developing peyotl; then `log-peyotl-curl`
turns on logging (and flushes the previous log!), `cat-peyotl-curl` shows the logged commands, and `stop-log-peyotl-curl` turns off logging.


    function log-peyotl-curl {
        export PEYOTL_CURL_LOG_FILE=/tmp/peyotl-curl-log.txt
        if test -f "$PEYOTL_CURL_LOG_FILE"
        then
            rm "$PEYOTL_CURL_LOG_FILE"
        fi
    }
    function cat-peyotl-curl {
        if ! test -f "$PEYOTL_CURL_LOG_FILE"
        then
            cat /tmp/peyotl-curl-log.txt
        else
            cat "$PEYOTL_CURL_LOG_FILE"
        fi
    }

    function stop-log-peyotl-curl {
        unset PEYOTL_CURL_LOG_FILE
    }



    $ sh tests/maintainer-test.sh



### Roundtrip tests
The following tests are triggered by running `bash tests/integration-tests.sh`

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
    java -jar "${NEXML_PARENT}/xml-validator/target/xml-validator-1.0-SNAPSHOT-jar-with-dependencies.jar" -s "${NEXML_PARENT}/nexml/xsd/nexml.xsd" $@

where xml-validator is a compiled clone of <a href="https://github.com/wiztools/xml-validator">https://github.com/wiztools/xml-validator</a> (you have to run <tt>mvn package</tt> to build)
and nexml is a clone of https://github.com/nexml/nexml

You can tweak this by deciding on your NEXML_PARENT dir and running:

    $ cd "${NEXML_PARENT}"
    $ svn checkout http://xml-validator.googlecode.com/svn/trunk/ xml-validator-read-only
    $ git clone https://github.com/nexml/nexml.git
    $ cd xml-validator-read-only
    $ mvn package



