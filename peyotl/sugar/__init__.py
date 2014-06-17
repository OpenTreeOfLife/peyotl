#!/usr/bin/env python
'''Brittle, shortcuts for doing things the explicit way
'''
treemachine = None
def _populate_globals():
    global treemachine
    from peyotl.api.treemachine import Treemachine
    treemachine = Treemachine()

_populate_globals()