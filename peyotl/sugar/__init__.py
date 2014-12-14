#!/usr/bin/env python
'''This subpackage provide shortcuts for doing things the explicit way.
importing this package will create the following wrappers around the web services:

    tnrs - (an peyotl.api.wrapper._TNRSServicesWrapper instance) for taxonomic
        name matching services. This service tries to find an OTT ID for a name.
'''
treemachine = None
taxomachine = None
phylesystem_api = None
oti = None
tnrs = None
taxonomy = None
tree_of_life = None
graph_of_life = None



def _populate_globals():
    global treemachine, oti, phylesystem_api, taxomachine, tnrs, taxonomy, tree_of_life, graph_of_life
    from peyotl.api import APIWrapper
    api_wrapper = APIWrapper()
    treemachine = api_wrapper.treemachine
    oti = api_wrapper.oti
    taxomachine = api_wrapper.taxomachine
    phylesystem_api = api_wrapper.phylesystem_api
    tnrs = api_wrapper.tnrs
    taxonomy = api_wrapper.taxonomy
    tree_of_life = api_wrapper.tree_of_life
    graph_of_life = api_wrapper.graph

_populate_globals()

