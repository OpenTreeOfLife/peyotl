---
layout: page
title: OTI wrappers
permalink: /oti-wrappers/
---
## OTI
oti indexes the values in the study nexson files managed by the [phylesystem-api](https://github.com/OpenTreeOfLife/phylesystem-api/blob/master/docs/README.md). This enables fast searching for text in different fields of the file. In [v2 of the Open Tree API](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs), it provides the `[domains]/studies/*` methods.

# Usage
The code examples below assume that you have created a wrapper via some action like:

    from peyotl.api import APIWrapper
    oti = APIWrapper().oti

# Attributes
*  `oti.study_search_term_set` is a read-only property that gives the set of terms that can be use to search for studies
*  `oti.tree_search_term_set` is a read-only property that gives the set of terms that can be use to search for trees
*  `oti.find_trees(query_dict, exact=<bool>, verbose=<bool>)` searches for a set of trees matching a query where the key in the `query_dict` is the name of the property to be searched and the value in the dict is the value that the property must have in order for the tree to match. For example: `oti.find_trees({'ot:ottTaxonName': 'Aponogeton ulvaceus'})` would return a record for every tree that has a taxon mapped to the ott taxon with the name "Aponogeton ulvaceus".
*  `oti.find_trees(prop=val, exact=<bool>, verbose=<bool>)` is a shorthand for searching for property `"ot:<prop>"` with value `val`. The preceding example would be: `oti.find_trees(ottTaxonName='Aponogeton ulvaceus'})` Note that 
the python rules for argument names mean that the `ot:` prefix must be removed from the property when you use this shorthand. It is added by the wrapper, so only 'ot:' properties can be searched with this trick
* `oti.find_studies(...)` supports the same two styles of invocation that as `find_trees`
* `oti.find_all_studies(verbose=<bool>)` returns a record for every study.



# TODO
1. the wrapper calls should migrate to using the v2 API.
2. Some output specifier (like the [PhyloSchema](PhyloSchema) could be used to obviate the need for `verbose` in the queries while providing more flexibility.
3. Chaining these calls to the phylesytem-api's GET could be more convenient.
4. Some sort of query language would allow for richer queries (intersections, unions...)