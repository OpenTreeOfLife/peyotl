---
layout: page
title: peyotl tutorials
permalink: /tutorial/
---

The tutorials subdirectory of peyotl contains some simple applications that use
    peyotl to access Open Tree of Life web service APIs.
These scripts are written in a fairly stereotyped way to make them easier to
    understand.
In each case the scripts end with a function `main` that configure an argparse
    ArgumentParser instance to process command line arguments.
At the end of each `main` function, there are calls to simple functions that occur
    earlier in each script.
These functions demonstrate peyotl functions.
So, if you are less interested in the command-line parsing, you can just look at the 
    functions before `main`.

### Getting help
Each of the example scripts in the tutorials directory takes a `-h` or `--help` argument that will result in an explanation of its command-line arguments.

# Overview of Open Tree of Life services

The 3 types of infrastructure that most users want to interact with are:

  1. the open tree taxonomy (OTT): the taxonomy used by the Open Tree of Life,
  2. phylesystem: the collection of trees from curated phylogenetic studies,
  3. the Graph of Life: the comprehensive, synthetic estimate of the phylogeny of life.

## Using the taxonomy.

The taxonomy plays a crucial role in constructing the Tree of Life because it allows
    different estimates of trees to be combinable in interesting ways.
Thus an early step in dealing with Open Tree of Life services involve mapping names for taxa to OTT.
Indeed, the primary workflow in the Open Tree of Life project itself consists of 
    importing new trees from the published literature into phylesystem and then
    mapping their tip labels to OTT so that they can contribute to the Graph of Life.


"Taxonomic Name Resolution Services" (TNRS) converts a name string to an OTT ID, 
    which is a number that uniquely identifies a taxon
    (see [the reference taxonomy wiki](https://github.com/OpenTreeOfLife/reference-taxonomy/wiki/General-information)
    for more details).
Using the OTT ID in subsequent interactions with the Open Tree of Life services saves
    us from having to deal with the headaches of taxonomic name matching (typos in
    names, orthographic variants of names, synonyms, and homonyms) in every API
    method call.

### Name to OTT ID: the `ot-tnrs-match-names.py` example script

By running:

    $ python tutorials/ot-tnrs-match-names.py Hominidae

from a terminal, you can trigger a TNRS service call for the name `Hominidae`.
This will obtain information on the taxon that matches that name (from the taxomachine web services).
The `ot_tnrs_match_names` function in that script performs this call, and
    the `match_and_print` function performs that call and demonstrates how
    you can extract the taxonomic information from the response.

Once again, [the reference taxonomy wiki](https://github.com/OpenTreeOfLife/reference-taxonomy/wiki/General-information)
    and [the API docs](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#tnrs)
    can be consulted for further documentation about the meaning of the flags and other information for a taxon.

Note that, because your commands typed at a terminal are interpretted by a shell, 
    you'll need to use quotes for multiword names when using this script:

So use:

    $ python tutorials/ot-tnrs-match-names.py 'Homo sapiens'

unless you want to search for "Homo" and "sapiens" as separate taxa.

Note that `ot-tnrs-match-names.py` has command line arguments to control two of the methods for narrowing or tightening the matching procedures:
  * "fuzzy" matches allows you to match names if there are typos or minor variations.
  * providing a "context" only searches for matches within a specific taxon. This helps you avoid inadvertently matching to a different taxon in another part of the tree of life.  Running:

    $ python tutorials/ot-tnrs-match-names.py any name here --context-name=bogus

will trigger an error (because "bogus" is not a valid context name). This error will
list the currently valid context names that can be used to narrow your search for a match.

For many subsequent API calls, the key information returned by the TNRS operation is the OTT ID.
This the `resp.ott_id` field for a wrapped response object called `resp`.

In the case of Hominidae, the OTT ID is 770311.
As, we'll see below, this ID can be used in other Open Tree of Life methods to refer to 
    this taxon concisely and without ambiguity.

### OTT ID to name: the `ot-taxon-info.py` example script
Once you are dealing with Open Tree of Life services, you will frequently encounter
    OTT IDs.
If you have an OTT ID, and you want some information about that taxon you can use the
    web services to learn about.

    $ python tutorials/ot-taxon-info.py 770311

is the reverse of the `tutorials/ot-tnrs-match-names.py` call discussed above.
It will print out the name (and some other info) for that OTT ID.

If you use:

    $ python tutorials/ot-taxon-info.py --include-lineage 770311

you'll get information on the ancestral taxa for the OTT ID that you passed in
    (770311, in this case) from the parent taxon all the way back to the root of
    tree of life.

### Name or OTT ID to published tree: the `ot-oti-find-tree.py` script

You may be interested in finding any published, curated tree in the phylesystem corpus
    that contains a particular taxon.
You can do this by asking the phylesystem indexing tool for a list of tree references, and
    then obtaining each tree from the phylesystem services.
The invocation:

    $ python tutorials/ot-oti-find-tree.py '{"ot:ottId": 84761}'

demonstrates how to search for a particular OTT ID.
Note that the argument for this script is a JSON object with keys explained
    in the [`tree_properties` section of the documentation of the `studies/properties` method of the API](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#properties).

In this case, we could have recovered the same set of trees by searching by
    the taxon name using:

    $ python tutorials/ot-oti-find-tree.py  '{"ot:ottTaxonName": "Chamaedorea frondosa"}'

Note that the taxonomic name matching here has to be exact.
Usually, you'll want to use the TNRS service described above to make sure that the taxonomic
    name that you are using agrees with the OTT taxonomic name.
That will give you more flexible matching of names to OTT IDs.
Then you can be confident the OTT ID-based query for a tree will not be a spurious
    match to a homonym (and that it won't fail because of a minor typo in the 
    input name).

### Getting a subtree of the synthetic tree of life produced by the Open Tree of Life

Earlier, we say that the animal family Hominidae has the OTT ID 770311
Running:

    $ python tutorials/ot-tree-of-life-mrca.py 770311

will print out some information about the node that corresponds to Hominidae in the 
    synthetic "graph of life". For this node, we just find out the (unstable) node ID
    and the fact that the node is a named taxon in OTT.

You can obtain the subtree rooted at this node by:

    $ python tutorials/ot-tree-of-life-mrca.py 770311 --subtree


Note that some taxa that are listed as monophyletic in OTT, are not recovered as 
    clades in the synthetic tree of life (becuase a published phylogenetic
    estimate disagrees with their monophyly and overrules the taxonomy).
For example, if we repeat the query with 34907 for the animal genus *Drosophila*:

    $ python tutorials/ot-tree-of-life-mrca.py 34907

We are informed this OTT ID is a valid OTT ID, but that it is "not recovered in the synthetic estimate of the tree of life".
The script also reports the information of the node in the synthetic tree which is
    the most recent common ancestor of all of the descendants of OTT ID 34097


You can list multiple OTT IDs with the `--subtree` option to ask the service to find the 
    most recent common ancestor of the IDs and return the entire subtree of the tree of life:

    $ python tutorials/ot-tree-of-life-mrca.py 793229 1069158 453621  --subtree

If you want the induced tree for a set of taxa (the tree that spans those leaves but is pruned down
    to include only those leaves), then you can use the `--induced-subtree` option.
Compare the results of the previous call to the results of:

    $ python tutorials/ot-tree-of-life-mrca.py 793229 1069158 453621  --induced-subtree
