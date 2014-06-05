# ![peyotl](https://raw.githubusercontent.com/OpenTreeOfLife/peyotl/master/doc/peyotl-logo.png)

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

## Installation

The code has been run on python 2.7.5. To install in developer mode:

    $ pip install -r requirements.txt
    $ python setup.py develop

## Configuration

If you run:

    $ cp extras/dot_peyotl ~/.peyotl

and then edit ~/.peyotl/config in your text editor to reflect the paths to 
the parent directory of the phylesystem, then the peyotl library can find
your local copy of phylesystem repos.

The environmental variable, PHYLESYSTEM_PARENT, if set will be used rather 
than the config-based value.

### Logging configuration

If PEYOTL_LOGGING_LEVEL is in the environment, then the behavior of 
the log is determined by environmental variables:
   PEYOTL_LOG_FILE_PATH filepath of log file (StreamHandler if omitted)
   PEYOTL_LOGGING_LEVEL (NotSet, debug, info, warning, error, or critical)
   PEYOTL_LOGGING_FORMAT  "rich", "simple" or "None" (None is default)

Otherwise, these logger settings are now controlled by a
 ~/.peyotl/config or the peyotl/default.conf file. The content to configure
 the logger looks like:

[logging]
level = debug
filepath = /absolute/path/to/log/file/here
formatter = rich

You probably want to replace the default behavior by specifying
PEYOTL_LOGGING_LEVEL or having a ~/.peyotl/config file.

# Testing

Running

    $ python setup.py test

will invoke python unittest, and running:

    $ sh test.sh

will run these test and some shell-based tests of interest to some developers.

## NexSON/NeXML

See https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/HoneyBadgerFish for full documentation
of the NeXML <-> NexSON conversion convention.

### Usage

    $ python scripts/nexson/nexson_nexml.py input -e 1.2 -o output

will read NeXML or NexSON as input and produce version 1.2 of the
honeybadgerfish NexSON and 

    $ python scripts/nexson/nexson_nexml.py input -e nexml -o output

to write NeXML.

The <code>-h</code> command line flag reports more details about the arguments.

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

# Roadmap

## Short term

  1. Improve tests of NexSON and complete transition to v1.2 syntax as the preferred syntax

  2. MTH needs to move NexSON validation from the API repo to peyotl

## Medium term (spring 2014)

  * Build up a set of utility phylogenetic functions that are agnostic to NexSON version
      like the current peyotl.nexson_syntax.add_resource_meta

  * Create a peyotl.native subpackage that implements the generic phylogenetic utilities
      under the assumption that the NexSON blob is v1.2

  * Improve struct_diff: better tests and better feature for representing sets of changes.

    * functions for comparing an ancestor to 2 descendants, for summarizing compatible or
        conflicting

  * Wrappers around web-service calls to open tree API web services

## Long term (summer 2014)

  * wrappers for treemachine/taxomachine web services.

  * wrappers for oti indexing web services.

  * support for input of parts of the OTT taxonomy, and taxonomic operations.

  * translation to DendroPy, BioPython, or PyCogent data structures from NexSON.

  * export to other phylogenetic file formats

# Thanks

peyotl is primarily written by Mark Holder, Emily Jane McTavish, and Jim Allman, 
but see the [contributors file] [6] for a more complete list
of people who have contributed code.

The fabulous <a href="http://karlgude.com/about/">Karl Gude</a> created the logo.

Several parts of the setup.py, logging, documentation, and test suite were 
based on Jeet Sukumraran's work in the [DendroPy](http://pythonhosted.org/DendroPy/) package.

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

****************

*Etymology*: According to Wikipedia, peyotl is the Nahuatl word for [*Lophophora williamsii*](http://en.wikipedia.org/wiki/Lophophora_williamsii).

[1]: http://blog.opentreeoflife.org/
[2]: https://github.com/OpenTreeOfLife/phylesystem
[3]: https://github.com/OpenTreeOfLife/api.opentreeoflife.org/
[4]: https://github.com/OpenTreeOfLife/taxomachine
[5]: https://github.com/OpenTreeOfLife/treemachine
[6]: https://raw.githubusercontent.com/OpenTreeOfLife/peyotl/master/CONTRIBUTORS.txt
