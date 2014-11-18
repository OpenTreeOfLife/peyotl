---
layout: page
title: taxomachine wrapper
permalink: /taxomachine-wrapper/
---
*NOTE* see the comments about the two styles of wrappers on [the API wrappers page](../api-wrappers). This page only describes the "thick" wrapper.

## Taxomachine
Taxomachine is a neo4j application that provides the web-services (TNRS and data access) around working the open tree taxonomy. In [v2 of the Open Tree API](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs), taxomachine provides provides the `[domains]/tnrs/*` and the the `[domains]/taxonomy/*` methods.

The code examples below assume that you have an instance of the wrapper via something like:

    from peyotl.api import APIWrapper
    taxo = APIWrapper().taxomachine

## TNRS-related Attributes
* `taxo.valid_contexts` read-only property of the set of names that can be used as "context" to narrow the name searching.
* `taxo.TNRS(["name 1", "name 2"...], context)` returns a list of TNRS results for each of the names passed in.


# TODO
1. should move to using v2 API methods in the implementation.
2. the `[domains]/taxonomy/*` methods need to be wrapped.