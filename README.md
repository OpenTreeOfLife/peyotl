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

4. call web services associated with Open Tree of Life's "synthetic"
    (running [treemachine] [5]);

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

****************

*Etymology* According to Wikipedia, peyotl was the Nahuatl word for [*Lophophora williamsii*](http://en.wikipedia.org/wiki/Lophophora_williamsii).

[1]: http://blog.opentreeoflife.org/
[2]: https://github.com/OpenTreeOfLife/phylesystem
[3]: https://github.com/OpenTreeOfLife/api.opentreeoflife.org/
[4]: https://github.com/OpenTreeOfLife/taxomachine
[5]: https://github.com/OpenTreeOfLife/treemachine