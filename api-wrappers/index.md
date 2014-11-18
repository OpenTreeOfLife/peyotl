---
layout: page
title: API wrappers
permalink: /api-wrappers/
---
peyotl has a set of wrappers to make it easier to call open tree of life web services.

To create a wrapper that includes handles to each of the services use:

    from peyotl.api import APIWrapper
    ot = APIWrapper()

the `ot` object in this example will use settings in your [peyotl configuration](../configuration) to choose what domains (e.g. devapi.opentreeoflife.org vs api.opentreeoflife.org) to connect to.

The key attributes of the APIWrapper that you are most likely to want to interact with are the wrappers around each service. Below is a list of attributes and links to the pages that describe each wrapper:

* `phylesystem_api` - the [phylesystem_api wrapper](../phylesystemapiwrapper)
* `oti` - the [oti wrapper](otiwrapper)
* `taxomachine` - the [Taxomachine wrapper](../taxomachinewrapper)
* `treemachine` - the [Treemachine wrapper](../treemachinewrapper)
