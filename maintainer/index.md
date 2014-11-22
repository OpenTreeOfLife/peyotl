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

If you are interested in running these "maintainer" tests:

    1. fork https://github.com/snacktavish/mini_phyl and
       https://github.com/snacktavish/mini_system on github (or some other
       server on which you have write permissions).

    2. From the top of the phylesystem repo directory:
    
    mkdir peyotl/test/data/mini_par
    cd peyotl/test/data/mini_par

    3. Used `git clone ...` to create clones of mini_phyl and mini_system
        in this directory.

At that point you should not see tests in the peyotl being skipped
with messages that refer to Peyotl not being configured for maintainer tests.


