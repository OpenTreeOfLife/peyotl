#!/usr/bin/env bash
curl -X POST http://api.opentreeoflife.org/treemachine/v1/getSyntheticTree -o getSyntheticTree.json -H "content-type:application/json" -d '{"treeID":"otol.draft.22", "format":"arguson", "maxDepth":"3", "subtreeNodeID":"3534540"}'  -s || echo "getSyntheticTree failed"
curl -X POST http://api.opentreeoflife.org/treemachine/v1/getDraftTreeSubtreeForNodes -o getDraftTreeSubtreeForNodes.json -H "content-type:application/json" -d '{"ottIds":[515698,515712,149491,876340,505091,840022,692350,451182,301424,876348,515698,1045579,267484,128308,380453,678579,883864,863991,3898562,23821,673540,122251,106729,1084532,541659]}'  -s || echo "getDraftTreeSubtreeForNodes failed"
curl -X POST http://api.opentreeoflife.org/treemachine/v1/getSynthesisSourceList -o getSynthesisSourceList.json   -s || echo "getSynthesisSourceList failed"
curl -X POST http://api.opentreeoflife.org/taxomachine/v1/autocompleteBoxQuery -o autocompleteBoxQuery.json -H "content-type:application/json" -d '{"queryString":"Endoxyla","contextName":"All life"}'   -s || echo "autocompleteBoxQuery failed"
curl -L http://api.opentreeoflife.org/phylesystem/v1/study_list -o study_list.json    -s || echo "study_list failed"
curl -L http://api.opentreeoflife.org/phylesystem/v1/study/pg_719 -o pg_719.json   -s || echo "pg_719 failed"
