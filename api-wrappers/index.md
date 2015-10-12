---
layout: page
title: API wrappers
permalink: /api-wrappers/
---
peyotl has a set of wrappers to make it easier to call open tree of life web services.

### API Wrapper factory
To create a factory for a wrapper use:

    from peyotl.api import APIWrapper
    a = APIWrapper()

the `a` object in this example will use settings in your [peyotl configuration](../configuration) to choose what domains (e.g. devapi.opentreeoflife.org vs api.opentreeoflife.org) to connect to. Or you can pass in a peyotl.wrapper.ConfigWrapper
object in to the initialization function of the APIWrapper to use instead of
your normal configuration.

The wrappers for individual servies created lazily as properties of the wrapper.

## 2 styles of wrappers
peyotl's wrappers pre-date the switch to [v2 of the Open Tree API](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs). 
The original version of the APIs were not very pythonic or standardized in terms of naming. So the peyotl wrappers provide more standardization of method names. These are referred to as the "thick" wrappers.

A working group hackathon came of with guidelines about wrapping open tree services
in any scripting language. See [their shared tests repo](https://github.com/OpenTreeOfLife/shared-api-tests) and discussion linked to by that README.
These method names correspond more closely to the current (v2) version of the API
method names. These conventions are supported by peyotl, as well. They will be referred to as the "shared interface" wrappers.

### Shared interface wrappers

The interface for these will not be described in detail, as you should be able to
use the [v2 of the Open Tree API documentation](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs) rather than peyotl-specific
documentation.

From the APIWrapper factory instance `a` (described above), you can get the individual wrappers with:

    tol = a.tree_of_life
    gol = a.graph
    tnrs = a.tnrs
    taxonomy = a.taxonomy
    study = a.study
    studies = a.studies

### Thick wrappers
These wrappers use names that are closer to the software implementing the 
method rather than the names used in the services in the API documentation. And
add some additional helper methods.

You can get these by accessing the property of the factory instance:

    phylesystem_api = a.phylesystem_api
    oti = a.oti
    taxomachine = a.taxomachine
    treemachine = a.treemachine

Below is a list of attributes and links to the pages that describe each wrapper:

* `phylesystem_api` - the [phylesystem_api wrapper](../phylesystem-api-wrapper)
* `oti` - the [oti wrapper](../oti-wrappers)
* `taxomachine` - the [Taxomachine wrapper](../taxomachine-wrapper)
* `treemachine` - the [Treemachine wrapper](../treemachine-wrapper)
