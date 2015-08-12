---
layout: page
title: Maintainer
permalink: /maintainer/
---

A few of the tests in the peyotl test suite (including some
tiggered by the `maintainer-test.sh` but not by `python setup.py test`).
require more setup than we expect a typical user to want to do.
In particular, you need some phylesystem-style repos on which you can
perform git actions - including pushes to remotes.

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
