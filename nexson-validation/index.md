---
layout: page
title: Format conversion
permalink: /nexson-validation/
---
## NexSON validation

See [the HoneyBadgerFish](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/HoneyBadgerFish) for full documentation
of the NeXML to NexSON conversion convention. The set of keys that are checked by peyotl's validator can be found at the bottom
of peyotl/nexson_validation/schema.py (in an admittedly cryptic format)


### Command-line

The NexSON validation code is used as a part of PUT and POST requests to the phylesystem-api. Warnings are allowed, but errors
result in the request being rejected.

You can run the validator from the command line with:

    $ ./scripts/nexson/validate_ot_nexson.py PATH-TO-NEXSON-FILE-HERE

If the script exits with code 0, then no errors were found. The standard output will also show a JSON description of warnings/errors.