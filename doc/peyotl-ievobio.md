# 
<div id="container">
 <img alt="2014 Architecture" src="peyotl-logo.png" />
</div>


by Open Tree of Life developers (primarily Mark T. Holder, Emily Jane McTavish, Duke Leto, and Jim Allman)

---
# peyotl

* Python library
1. implements much of the [phylesystem-api](https://github.com/OpenTreeOfLife/phylesystem-api)
1. helps you interact with a local version of the [phylesystem](https://github.com/OpenTreeOfLife/phylesystem).
2. call open tree web services for:
    * interacting with the "central" phylesystem-api
    * resolution of taxonomic names to the [Open Tree Taxonomy](https://github.com/OpenTreeOfLife/reference-taxonomy/wiki)
    * queries against an estimate of the Tree of Life

---
# Open Tree of Life
* we've adopted a service oriented architecture.
* things have gotten a bit complex...

---
<div id="container">
 <img alt="2014 Architecture" src="images/architecture-user-2014.svg" width="800" height="600" />
</div>

---
# Open Tree of Life APIs

* come to the [Tree-for-all hackathon!](https://docs.google.com/document/d/10bjPVPnITJKvIt9ZWsM5-IK7h7H7QooWWwZBLnZ9cEA)
* [https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs)
* note the "v1": `...org/treemachine/`**v1**`/getDraftTree...`

---
# `peyotl` api wrappers

* make accessing the API simpler and more "pythonic"
* improve stability - when the Open Tree of Life API version changes, the `peyotl` interface won't (hopefully)

---
# Taxonomic Name Resolution Service
* calling in "taxomachine" by Cody Hinchliff.

<pre  id="snippet">
from peyotl.sugar import taxomachine
print taxomachine.TNRS('Anolis sagrei')
</pre>
returns a object summarizing the possible matches.

---
# Getting a pruned version of the "full tree"
<pre id="snippet">
from peyotl.sugar import treemachine as tm
o = [515698, 515712, 149491, 876340, 505091, 840022, 692350, 451182, 301424, 876348, 515698, 1045579, 267484, 128308, 380453, 678579, 883864, 863991, 3898562, 23821, 673540, 122251, 106729, 1084532, 541659]
r = tm.get_synth_tree_pruned(ott_ids=o)
</pre>

returns the tree (currently only in an odd, in-house format called "Arguson")

---
# Searching the input trees
* calling in "oti" by Cody Hinchliff.

<pre id="snippet">
from peyotl.sugar import oti
n = 'Aponogeoton ulvaceus'
print oti.find_trees(ottTaxonName=n)
</pre>

returns a list of objects listing studyID and treeID

---
# Obtaining an input tree
<pre id="snippet">
from peyotl.api import PhylesystemAPI
pa = PhylesystemAPI(get_from='api')
print pa.get('pg_10',
             tree_id='tree3',
             subtree_id='ingroup',
             format='newick')
</pre>
returns the ingroup of "tree3¨ from study "pg_10" in newick.

---
# get an input tree
<pre id="snippet">
pa = PhylesystemAPI(get_from='api',
                    transform='server')
</pre>
<pre id="snippet">
pa = PhylesystemAPI(get_from='api',
                    transform='client')
</pre>
<pre id="snippet">
pa = PhylesystemAPI(get_from='local')
</pre>
<pre id="snippet">
pa = PhylesystemAPI(get_from='external')
t =  pa.get('pg_10',...
</pre>

---
# "api" mode
<pre id="client">
request tree and format
</pre>
<pre id="server">
look up location of study NexSON file
</pre>
<pre id="server">
read NexSON file
</pre>
<pre id="server">
extract tree
</pre>
<pre id="server">
convert to newick
</pre>
<pre id="server">
return to client
</pre>

---
# "api"+ transform
<pre id="client">
request tree and format
</pre>
<pre id="server">
look up location of study NexSON file
</pre>
<pre id="server">
read NexSON file
</pre>
<pre id="server">
return to client
</pre>
<pre id="client">
extract tree
</pre>
<pre id="client">
convert to newick
</pre>
