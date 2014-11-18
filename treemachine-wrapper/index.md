---
layout: page
title: treemachine wrapper
permalink: /treemachine-wrapper/
---
*NOTE* see the comments about the two styles of wrappers on [the API wrappers page](../api-wrappers). 

## Treemachine
Treemachine is a neo4j application that provides the web-services (TNRS and data access) around working the open tree synthetic tree and the graph of life from
well-curated published trees. In [v2 of the Open Tree API](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs), treemachine provides provides the `[domains]/tree_of_life/*` and the the `[domains]/tree_of_life/*` methods.

The code examples below assume that you have an instance of the wrapper via something like:

    #!/usr/bin/env
    from peyotl.api import APIWrapper
    tm = APIWrapper().treemachine
    tax = APIWrapper().taxomachine
    # Get info about synthesis
    info = tm.get_synthetic_tree_info()
    # Get tree ID
    tid = info['tree_id']
    # Get the OTT IDs from taxomachine
    human, gorilla = tax.names_to_ott_ids_perfect(['homo sapiens', 'Gorilla gorilla'])
    mrca_info = tm.mrca(ott_ids=[human, gorilla])
    mrca_node_id = mrca_info['mrca_node_id']
    # fetch a few levels of the tree:
    newick = tm.get_synthetic_tree(tid, format="newick", node_id=mrca_node_id)['newick']
    # pruned is silly for just 2 leaves, but...
    newick = tm.get_synth_tree_pruned(ott_ids=[human, gorilla])['subtree']
    # Get list of dicts describing the version of each input tree
    inputs = tm.get_synthetic_tree_id_list()


### shared-API wrapper-style

    from peyotl.api import APIWrapper
    tol = APIWrapper().tree_of_life
    # Get info about synthesis
    info = tol.about()
    # Get list of dicts describing the version of each input tree
    tol.about()['study_list']
    # Get tree ID
    tid = info['tree_id']
    # Get root node ID
    nid = info['root_node_id']
    # fetch a few levels of the tree:
    newick = tm.get_synthetic_tree(tid, format="newick", node_id=nid, max_depth=2)




## TNRS-related Attributes
* `taxo.valid_contexts` read-only property of the set of names that can be used as "context" to narrow the name searching.
* `taxo.TNRS(["name 1", "name 2"...], context)` returns a list of TNRS results for each of the names passed in.

    from peyotl.api import APIWrapper
    oti = APIWrapper().oti
