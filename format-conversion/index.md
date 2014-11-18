---
layout: page
title: Format conversion
permalink: /format-conversion/
---
## NexSON/NeXML

See [the HoneyBadgerFish](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/HoneyBadgerFish) for full documentation
of the NeXML to NexSON conversion convention.

### Usage

    $ python scripts/nexson/nexson_nexml.py input -e 1.2 -o output

will read NeXML or NexSON as input and produce version 1.2 of the
honeybadgerfish NexSON and 

    $ python scripts/nexson/nexson_nexml.py input -e nexml -o output

to write NeXML.

The <code>-h</code> command line flag reports more details about the arguments.

## NexSON/Newick

    $ python scripts/nexson/nexson_newick.py -h

Explains the options for running a NexSON to newick converter. A tree's ID
can be specified, and the field used to label the tips can be chosen from the
command-line options.
