# ![peyotl](https://raw.githubusercontent.com/OpenTreeOfLife/peyotl/master/doc/peyotl-logo.png)
[![Build Status](https://secure.travis-ci.org/OpenTreeOfLife/peyotl.png)](http://travis-ci.org/OpenTreeOfLife/peyotl)

<code>peyotl</code> is a python package written to make it easier to
interact with the software produced by the [Open Tree of Life project] [1].
Specifically, to:

1. interact with a local version of the [phylesystem] [2] repository of 
    curated phylogenetic studies ;

2. call web services associated with the studies (served by web app 
    running the [phylesystem-api code] [3]);

3. call web services associated with taxonomic resolution services
    (running [taxomachine] [4] );

4. call web services associated with Open Tree of Life's "synthetic" estimate
    of the tree of life (running [treemachine] [5]);

5. call web services associated with an annotation database (that
     we have not built yet)

Currently peyotl is used to implement most of the functionality in the 
[phylesystem-api] [3] backend of the study curation tool.

# Instructions
You probably want to be using a virtualenv. Then you can:

    $ pip install -r requirements.txt
    $ python setup.py develop

For full(er) documentation, check out our [http://opentreeoflife.github.io/peyotl/](http://opentreeoflife.github.io/peyotl/) documentation site.

# Testing

Use:
    python setup.py test

to trigger the unittests. The wiki https://github.com/OpenTreeOfLife/peyotl/wiki/testing
describes the other tests scripts.


# Thanks

peyotl is primarily written by Mark Holder, Emily Jane McTavish, and Jim Allman, 
but see the [contributors file] [6] for a more complete list
of people who have contributed code.

The fabulous <a href="http://karlgude.com/about/">Karl Gude</a> created the logo.

Several parts of the setup.py, logging, documentation, and test suite were 
based on Jeet Sukumraran's work in the [DendroPy](http://pythonhosted.org/DendroPy/) package.

The tree/node iteration functions in peyotl.phylo.tree are also adapted from DendroPy.

The sortattr.xslt stylesheet (which is only used in round-trip testing) is from 
   http://stackoverflow.com/questions/1429991/using-xsl-to-sort-attributes

The peyotl.phylesystem.git_actions (and the tests) were a part of the api.opentreeoflife.org
    repo which was primarily the work of Duke Leto (at that time).

Jim Allman, Karen Cranston, Cody Hinchliff, Mark Holder, Peter Midford, and Jonathon Rees
all participated in the discussions that led to the NexSON mapping.

The peyotl/test/data/nexson/phenoscape/nexml test file is from
    https://raw.github.com/phenoscape/phenoscape-data/master/Curation%20Files/completed-phenex-files/Characiformes/Buckup_1998.xml
    PhenoscapeKB, [U.S. National Evolutionary Synthesis Center], http://kb.phenoscape.org; [Feb 16, 2014]
    The citation for the data is in the nexml doc itself.

peyotl includes the `ez_setup.py` tool from [setuptools](https://pypi.python.org/pypi/setuptools)
    To satisfy the Python Software Foundation license we note here that peyotl does not 
    alter the python sourcee code itself. By installing the package you enable the python
    interpreter to find the code included in this package for interacting with open tree of life
    data and web services.



****************

*Etymology*: According to Wikipedia, peyotl is the Nahuatl word for [*Lophophora williamsii*](http://en.wikipedia.org/wiki/Lophophora_williamsii).

[1]: http://blog.opentreeoflife.org/
[2]: https://github.com/OpenTreeOfLife/phylesystem
[3]: https://github.com/OpenTreeOfLife/phylesystem-api
[4]: https://github.com/OpenTreeOfLife/taxomachine
[5]: https://github.com/OpenTreeOfLife/treemachine
[6]: https://raw.githubusercontent.com/OpenTreeOfLife/peyotl/master/CONTRIBUTORS.txt
