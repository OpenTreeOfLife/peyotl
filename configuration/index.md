---
layout: page
title: Configuration
permalink: /configuration/
---
There are some environmental variables that peyotl is sensitive to.
But, for the most part, configuration is done using config files.
The default location for the config file is `~/.peyotl/config`, however
you can override that by have a variable in your environment
called `PEYOTL_CONFIG_FILE` which holds the full path to the 
config file that you'd like to use.

Using config-dependent is intended
to support simultaneous use of the library by typical users (with no
config file) and testers of open tree software (who often want very abnormal
configurations to exercise rarely used features or test services that 
have not been released yet). Config variable are used when the runtime variable
does not belong as a part of a function/method call because it is too low-level
and almost never changes in typical use cases.

Config-file-dependent behavior can be a bit cryptic, but setting the logging 
level to a low setting (trace or debug) will result in messages indicating which 
config files have been used.

### Syntax
The syntax for the config file is the standard [INI file](http://en.wikipedia.org/wiki/INI_file) format.

### Creating a configuration
The easiest way to get a framework for a config file is to copy the example `dot_peyotl` directory
to the default location:

    $ mkdir ~/.peyotl
    $ cp extras/dot_peyotl/config ~/.peyotl/config

and then edit `~/.peyotl/config` in your text editor to reflect the paths to 
the parent directory of the phylesystem, then the peyotl library can find
your local copy of phylesystem repos.

## Logging configuration
If `PEYOTL_LOGGING_LEVEL` is in the environment, then the behavior of 
the log is determined by environmental variables:

* `PEYOTL_LOG_FILE_PATH` filepath of log file (StreamHandler if omitted)
* `PEYOTL_LOGGING_LEVEL` (NotSet, debug, info, warning, error, or critical)
* `PEYOTL_LOGGING_FORMAT`  "rich", "simple" or "None" (None is default)

Otherwise, these logger settings are now controlled by a
 `~/.peyotl/config` or the `peyotl/default.conf` file (packaged inside
 the `peyotl` package. 
 The content to configure
 the logger looks like:


    [logging]
    level = debug
    filepath = /absolute/path/to/log/file/here
    formatter = rich

You probably want to replace the default behavior by specifying
`PEYOTL_LOGGING_LEVEL` or having a `~/.peyotl/config` file.

### [API wrappers](../api-wrappers/)
Peyotl has wrappers to make it easier to communicate with Open Tree 
of Life web services. Because we use peyotl in testing the services
as we deploy, the domains where the APIs are configurable:

    [apis]
    phylesystem_api = https://api.opentreeoflife.org
    oti = https://api.opentreeoflife.org
    taxomachine = https://api.opentreeoflife.org
    treemachine = https://api.opentreeoflife.org
    api_version = 2
    raw_urls = false

### [Phylesystem](../phylesystem)
If you are performing operations that use a local version of the phylesystem 
git document store, you need to tell peyotl where to find the phylsystem repositories.
If the environmental variable `PHYLESYSTEM_PARENT` is not set 
then the config file will be used. For example:

    [phylesystem]
    parent = /home/username/phylesystem/shards

Peyotl will treat any git directory in this parent that has a `study` subdirectory as if it was
a shard of phyleystem.

**WARNING:** the "parent" should point to the "shards" directory of your local copy of the phylesystem 
repository. A better name for this setting would have been `[phylesystem]/shards`

Note (in the table below) that the phylesystem section can also set a max_file_size (in bytes).

#### example of bootstrapping the phylesystem configuration on a new machine

    cd ~/somedir
    git clone https://github.com/OpenTreeOfLife/phylesystem.git
    cd phylesystem
    bash pull-studies.bash
    cd shards
    echo "Now set your 'parent' variable in the '[phylesystem]' section of ~/.peyotl/config to have the value   $PWD"


### OTT
Currently, peyotl has very little functionality related to dealing with OTT.
However, the parent of the current version of OTT can be specified using:

    [ott]
    parent = /home/username/ott2.6

# Summary of config settings

| Section | param | default | usage |
|---------|-------|---------|-------|
| logging | level | WARNING | filter for what level of messages are displayed |
| logging | formatter | '%H:%M:%S' | formatter string for messages. See https://docs.python.org/2/library/logging.html#formatter-objects | 
| logging | filepath | None | filepath for log file |
| apis | oti | https://api.opentreeoflife.org | Domain of oti server for wrapper around oti |
| apis | phylesystem_api | https://api.opentreeoflife.org | Domain of phylesystem-api server for wrapper around that service |
| apis | taxomachine | https://api.opentreeoflife.org | Domain of taxomachine server for wrapper around that service |
| apis | treemachine | https://api.opentreeoflife.org | Domain of treemachine server for wrapper around that service |
| apis | phylesystem_get_from | external | source for a phylesystem-api wrapper's study GET operations (choices are "local", "api", and "external") | 
| apis | phylesystem_transform | client | where a phylesystem-api wrapper should perform transformations between different NexSON versions (choices are "client" and "server") |
| apis | phylesystem_refresh | never | when a local phylesystem wrapper should call "git pull" |
| apis | api_version | "2" | "1" to specify use of the <a href="https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs-V1">v1</a> open tree API rather than api <a href="https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs">v2</a> in the wrapped apis. |
| apis | X_api_version | "2" | where X = oti, treemachine or taxomachine. Acts like the api_version setting, but overrides it and only affects the wrappers for the indicated service  |
| apis | raw_urls | "false" | "true" to use the default localhost URLs without and proxy-pass magic in the api wrappers |
| apis | X_raw_urls | "false" | where X = oti, treemachine or taxomachine. Acts like the raw_urls setting, but overrides it and only affects the wrappers for the indicated service  |
| phylesystem | parent | None | top-level (usually the "shards" directory) directory that holds each of the phylesystem-# repos (if you have a local version of these repos) | 
| phylesystem | max_file_size | None | maximum file size of a single JSON in a commit to phylesystem in number of bytes | 


