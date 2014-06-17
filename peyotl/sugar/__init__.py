#!/usr/bin/env python
'''Brittle, shortcuts for doing things the explicit way
'''
treemachine, taxomachine, phylesystem_api, oti = None, None, None, None
def _populate_globals():
    global treemachine, oti, phylesystem_api, taxomachine
    from peyotl.api import APIWrapper
    api_wrapper = APIWrapper()
    treemachine = api_wrapper.treemachine
    oti = api_wrapper.oti
    taxomachine = api_wrapper.taxomachine
    phylesystem_api = api_wrapper.phylesystem_api

_populate_globals()