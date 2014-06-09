#!/bin/bash
# See https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs
curl -X POST http://api.opentreeoflife.org/treemachine/v1/getSyntheticTree -H "content-type:application/json" -d '{"treeID":"otol.draft.22", "format":"arguson", "maxDepth":"3", "subtreeNodeID":"3534540"}'>out-curl-synthetic.json|| echo 'synthetic failed'
curl -X POST http://api.opentreeoflife.org/treemachine/v1/getDraftTreeSubtreeForNodes -H "content-type:application/json" -d '{"ottIds":[515698,515712,149491,876340,505091,840022,692350,451182,301424,876348,515698,1045579,267484,128308,380453,678579,883864,863991,3898562,23821,673540,122251,106729,1084532,541659]}' >out-curl-synth-subtree.json || echo 'synth-subtree failed'
curl -X POST http://api.opentreeoflife.org/treemachine/v1/getSynthesisSourceList >out-curl-synth-src-list.json || echo 'synth-src-list failed'
curl -X POST http://api.opentreeoflife.org/taxomachine/v1/autocompleteBoxQuery -H "content-type:application/json" -d '{"queryString":"Endoxyla","contextName":"All life"}' >out-curl-tnrs.json || echo 'tnrs failed'
curl -L http://api.opentreeoflife.org/phylesystem/v1/study_list  >out-curl-phylesystem-study-list.json || echo 'phylesystem-study-list failed'
curl -L http://api.opentreeoflife.org/phylesystem/v1/study/pg_719 >out-curl-phylesystem-get.json || echo 'phylesystem-get failed'
