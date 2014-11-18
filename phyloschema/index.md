---
layout: page
title: PhyloSchema
permalink: /phyloschema/
---
This class (importable from `peyotl.nexson_syntax`) provides a simple container for holding the set of variables needed to convert from one format to another (with error checking). The primary motivation for this class is to:

1. generate type conversion errors up front when some one requests a particular coercion. For example, this allows the phylesystem api to raise an error before it fetches the data in cases in which the user is requesting a format/content combination is not currently supported (or not possible)
2. allow that agreed-upon coercion to be done later with a simple call to convert or serialize. So the class acts like a closure that can transform any nexson to the desired format (if NexSON has the necessary content)

This class is used internally by peyotl. Client code may have to create instances of PhyloSchema objects, but should not need to call methods of the objects.

## Initialization
`PhyloSchema.__init__(schema, **kwargs)` creates an object where the arguments are:

* `schema` `None` one of `nexson` | `newick | `nexml` | `nexus`
* `content` one of `file` | `meta` | `otu` | `otumap` | `otus` | `study` | `subtree` | `tree`
* content_id = None if `content` ==  `study` or `meta`) <br/>
a string if `content` is `file`, `otu`, `otumap`, `otus`, `tree`, or <br/>
a tuple of strings (TREE_ID, NODE_ID) if `content`==`tree`
* `type_ext` (only used if `schema` is None to infer schema using the rule<br/>
                    '.nexson' -> 'nexson',<br/>
                    '.nexml'-> 'nexml',<br/>
                    '.nex'-> 'nexus',<br/>
                    '.tre'-> 'newick',<br/>
                    '.nwk'-> 'newick',<br/>
* `output_nexml2json` used if the schema is NexSON should be `0.0.0`, `1.0.0`, `1.2.1` specifies the version of NexSON
* `format_str` acts like `schema` (but has lower priority than type_ext and output_nexml2json)
* `version` acts like `output_nexml2json`
* `otu_label` (see below)

If OTUs are requested, the `otu_label` specifies what field will be used to represent the otu. This should
be `ot:originalLabel`, `ot:ottId`, or `ot:ottTaxonName` (but the value is not case sensitive).

## `create_content_spec` factory
`create_content_spec` returns a PhyloSchema object.
As seen above, the `PhyloSchema(...)` initializer is quite complex and its generic nature leads to some cryptic names (e.g. `content_id` can hold a tree ID, or an OTU ID depending on the `content` argument).
The `create_content_spec(**kwargs)` supports some more specific arguments that lead to clearer
calls on the client side. The arguments for this function support:

* `format` as an alias for `format_str`
* `nexson_version` as an alias of `version`
* `tip_label` as an alias for `otu_label`
* `tree_id=TREEID, subtree_id=NODEID` or `tree_id=TREEID, node_id=NODEID` as aliases for `content="subtree", content_id=(TREEID, NODEID)`
* `tree_id=TREEID`  as an alias for `content="tree", content=TREEID`
* `otus_id=OTUSID` as an alias for `content="otus", content=OTUSID`
* `otu_id=OTUID` as an alias for `content="otu", content=OTUID`



