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


# Thanks

Several parts of the setup.py, logging, documentation, and test suite were 
based on Jeet Sukumraran's work in the [DendroPy](http://pythonhosted.org/DendroPy/) package.

****************

*Etymology* According to Wikipedia, peyotl was the Nahuatl word for [*Lophophora williamsii*](http://en.wikipedia.org/wiki/Lophophora_williamsii).

[1]: http://blog.opentreeoflife.org/
[2]: https://github.com/OpenTreeOfLife/phylesystem
[3]: https://github.com/OpenTreeOfLife/api.opentreeoflife.org/
[4]: https://github.com/OpenTreeOfLife/taxomachine
[5]: https://github.com/OpenTreeOfLife/treemachine