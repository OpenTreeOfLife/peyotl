# peyotl

A python package to make it easier to access web services and data
associated with the [Open Tree of Life project] [1].

This is intended to hold utility code to make it easier to:

1. interact with a local version of the [phylesystem] [2] repository of 
    curated phylogenetic studies ;

2. call web services associated with the studies (served by web app 
    running the [api.opentree.org code] [3]);

3. call web services associated with taxonomic resolution services
    (running [taxomachine] [4] );

4. call web services associated with Open Tree of Life's "synthetic" estimate
    of the tree of life (running [treemachine] [5]);

5. call web services associated with an annotation database (that
     we have not built yet)

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

    $ python scripts/nexson/nexson_nexml.py input -o output

will read NeXML or NexSON as input and produce the other format in a file called output.

You can use the -m to specify the conversion mode. It expects two letter code for the 
source and destination formats: 
  x for NeXML,
  j for NexSON (using the HoneyBadgerFish convention),
  b for a direct BadgerFish translation of NeXML.

So to convert from HoneyBadgerFish to BadgerFish run:

    $ python nexson_nexml.py -m jb -o someoutfile.json otu.json

### Roundtrip tests

A test of the available format conversions (without NeXML validation) can be run with:

    $ sh peyotl/test/check_nexson_nexml_clique.sh peyotl/test/data/nexson/otu.json


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

# Thanks

Several parts of the setup.py, logging, documentation, and test suite were 
based on Jeet Sukumraran's work in the [DendroPy](http://pythonhosted.org/DendroPy/) package.

The sortattr.xslt stylesheet (which is only used in round-trip testing) is from 
   http://stackoverflow.com/questions/1429991/using-xsl-to-sort-attributes other code by Mark Holder.

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


