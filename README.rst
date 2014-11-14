peyotl
======

.. image:: https://raw.githubusercontent.com/OpenTreeOfLife/peyotl/master/doc/peyotl-logo.png


peyotl is a python package written to make it easier to
interact with the software produced by the `Open Tree of Life project`_.
Specifically, to:

1. interact with a local version of the phylesystem_ repository of 
    curated phylogenetic studies ;

2. call web services associated with the studies (served by web app 
    running the `phylesystem api`_ code);

3. call web services associated with taxonomic resolution services
    (running taxomachine_ );

4. call web services associated with Open Tree of Life's "synthetic" estimate
    of the tree of life (running treemachine_);

5. call web services associated with an annotation database (that
     we have not built yet)

Currently peyotl is used to implement most of the functionality in the 
`phylesystem api`_ backend of the study curation tool.

Instructions
------------

::

    virtualenv pey
    . pey/bin/activate
    pip install -r requirements.txt
    python setup.py develop
    python setup.py test

performs the basic installation and test. For full(er) documentation, check out the wiki_.


Thanks
------

Thanks to NSF_ and HITS_ for funding support.

peyotl is primarily written by Mark Holder, Emily Jane McTavish, and Jim Allman, 
but see the CONTRIBUTORS_ file for a more complete list
of people who have contributed code.

The fabulous `Karl Gude`_ created the logo.

Several parts of the setup.py, logging, documentation, and test suite were 
based on Jeet Sukumraran's work in the DendroPy_ package.

The sortattr.xslt stylesheet (which is only used in round-trip testing) is from 
   http://stackoverflow.com/questions/1429991/using-xsl-to-sort-attributes

The peyotl.phylesystem.git_actions (and the tests) were a part of the api.opentreeoflife.org
    repo which was primarily the work of Duke Leto (at that time).

Jim Allman, Karen Cranston, Cody Hinchliff, Mark Holder, Peter Midford, and Jonathon Rees
all participated in the discussions that led to the NexSON mapping.

The peyotl/test/data/nexson/phenoscape/nexml test file is from
    https://raw.github.com/phenoscape/phenoscape-data/master/Curation%20Files/completed-phenex-files/Characiformes/Buckup_1998.xml
    Phenoscape file (download), NESCent_ [Feb 16, 2014] The citation for the data is in the nexml doc itself.

****************

*Etymology*: According to Wikipedia, peyotl is the Nahuatl word for `Lophophora williamsii`_.

.. _Open Tree of Life project: http://blog.opentreeoflife.org/
.. _phylesystem: https://github.com/OpenTreeOfLife/phylesystem
.. _phylesystem api: https://github.com/OpenTreeOfLife/api.opentreeoflife.org/
.. _taxomachine: https://github.com/OpenTreeOfLife/taxomachine
.. _treemachine:  https://github.com/OpenTreeOfLife/treemachine
.. _CONTRIBUTORS: https://raw.githubusercontent.com/OpenTreeOfLife/peyotl/master/CONTRIBUTORS.txt
.. _wiki: https://github.com/OpenTreeOfLife/peyotl/wiki
.. _Karl Gude: http://karlgude.com/about/
.. _DendroPy: http://pythonhosted.org/DendroPy/
.. _Lophophora williamsii: http://en.wikipedia.org/wiki/Lophophora_williamsii
.. _NSF: http://www.nsf.gov
.. _HITS: http://www.h-its.org/english
.. _NESCent: http://kb.phenoscape.org
