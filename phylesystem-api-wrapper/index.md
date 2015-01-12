---
layout: page
title: Phylesystem API wrappers
permalink: /phylesystem-api-wrapper/
---
*NOTE* see the comments about the two styles of wrappers on [the API wrappers page](../api-wrappers). This page only describes the "thick" wrapper.

## The phylesystem-api
The [phylesystem-api](https://github.com/OpenTreeOfLife/phylesystem-api/blob/master/docs/README.md) 
provides web services for obtaining the corpus of phylogenetic studies that are inputs into the
Open Tree of Life project. This tool implements the `[domain]/v2/study/*` web-services of the [API](https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs).

# Methods
The docs below assume that you have created a wrapper via some action like:

    from peyotl.api import APIWrapper
    ps = APIWrapper().phylesystem_api

## Primary attributes:
1. `ps.study_list` a read-only property that is a shallow copy of the list of all of the study IDs in the phylesystem.
2. `ps.get(study_id)` fetches the requested study. The attributes of the response are described [here](https://github.com/OpenTreeOfLife/phylesystem-api/blob/master/docs/README.md#get-response).
3. `ps.get(study_id, schema=x)` requests a subset of the study info for study `study_id`. The `schama` argument should be a [PhyloSchema](phyloschema) object that determines what type of data should be returned, and the format for that data.
4. `ps.get(study_id, content=x, **kwargs)` Like the previous call, but uses [the create_content_spec trick](phyloschema#create_content_spec-factory) with args (content=content, **kwargs) to create the Schema object. This is just a bit of syntactic sugar to make the client code terse but clear.


## Additional (rarely used) attributes: 
1. `ps.phylesytem_config` read-only property holding the details about how the server's phylesytem is configured
2. `ps.phylesystem_obj` read-only property that is a handle to the wrapper of the low-level Phylesystemobject. This is
useful if you are using a "local" PhylesystemAPI wrapper (see below), because you can then perform
operations like iterating over the studies.
3. `ps.repo_nexml2json` read-only property holding  the version of NexSON syntax stored in the git repository.
4. `ps.domain` property holding the domain of the server.

## Controlling the source of the study data
The data for these studies is actually stored in a git repository. 
So, intensive use of a lot of study data is most efficiently accomplished by cloning the 
  git repo and performing operations on the local filesystem (rather than web-services).
To support both web-service and local operations, the wrapper around the [phylesystem-api](https://github.com/OpenTreeOfLife/phylesystem-api) is one of the "thickest" wrappers in peyotl. 

There are 4 sets of initialization variables supported:

1. `PhylesystemAPI(get_from='local')` uses a copy of the [phylesystem](../phylesystem/) repository present on your local machine;
2. `PhylesystemAPI(get_from='external')` accesses study data via URLs on GitHub;
3. `PhylesystemAPI(get_from='api', transform='client')` fetches data from a remote instance of the phylesystem-api, but does any translation of the data into another form on the client machine; and
4. `PhylesystemAPI(get_from='api', transform='server')` fetches data from a remote instance of the phylesystem-api and requests that the server do any translation of the data.

The default mode is `external`

If you are creating a PhylesystemAPI wrapper via a higher level APIWrapper, you can tweak the arguments used to create the PhylesystemAPI instance using the `phylesystem_api_kwargs` argument:    

    ot = APIWrapper(phylesystem_api_kwargs={'get_from':'api'})

These options are arranged from least taxing on the open tree of life servers to most taxing.

## Attributes only available if the wrapper use the "API" mode
Only available if you using `get_from='api'`:
1. `get_external_url(study_id)` Returns a URL from which you can fetch the data in a raw, un modified form.
2. `push_failure_state` read-only property. A tuple: the boolean for whether or not pushes succeed, and the entire object returned by a call to push_failure on the phylesystem-api.
3. `unmerged_branches()` returns a list of branches of the data that could not be merged to master.

# TODO
1. Need to add client-side support for the `[domain]/v2/study/*/file/*` service, once it is deployed.
2. It might be nice to add a transform function as an argument to the `.get(...)` methods to perform a post-fetch, pre-return tranformation on the data.
3. Expanding the [PhyloSchema](PhyloSchema) class to support more formats would be nice.


