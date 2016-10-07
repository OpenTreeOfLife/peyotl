#!/usr/bin/env python
"""This subpackage provide shortcuts for doing things the explicit way.
importing this package will create the following wrappers around the web services:

    tnrs - (an peyotl.api.wrapper._TNRSServicesWrapper instance) for taxonomic
        name matching services. This service tries to find an OTT ID for a name.
"""
treemachine = None
taxomachine = None
phylesystem_api = None
collections_api = None
amendments_api = None
# favorites_api = None
oti = None
tnrs = None
taxonomy = None
tree_of_life = None
graph_of_life = None
studies = None


def _populate_globals():
    global treemachine, oti, phylesystem_api, collections_api, amendments_api, taxomachine, tnrs, \
        taxonomy, tree_of_life, graph_of_life, studies
    from peyotl.api import APIWrapper
    api_wrapper = APIWrapper()
    treemachine = api_wrapper.treemachine
    oti = api_wrapper.oti
    taxomachine = api_wrapper.taxomachine
    phylesystem_api = api_wrapper.phylesystem_api
    collections_api = api_wrapper.collections_api
    # amendments_api = api_wrapper.amendments_api
    # global favorites_api
    # favorites_api = api_wrapper.favorites_api
    tnrs = api_wrapper.tnrs
    taxonomy = api_wrapper.taxonomy
    tree_of_life = api_wrapper.tree_of_life
    graph_of_life = api_wrapper.graph
    studies = api_wrapper.studies


_populate_globals()
