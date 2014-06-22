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

