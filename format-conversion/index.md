---
layout: page
title: Format conversion
permalink: /format-conversion/
---
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
