#!/usr/bin/env python
"""
Small library for conducting operations over the
entire set of NexSON files in one or more phylesystem
repositories.
"""
# Some imports to help our py2 code behave like py3
from __future__ import absolute_import, print_function, division

__version__ = '1.0.1dev'  # sync with setup.py

from peyutil import (read_as_json,
                     write_as_json)
from peyotl.collections_store import (collection_to_included_trees,
                                      concatenate_collections,
                                      tree_is_in_collection)
from peyotl.nexson_syntax import (detect_nexson_version,
                                  _is_by_id_hbf)
from peyotl.phylesystem.phylesystem_umbrella import Phylesystem
from peyotl.phylo.entities import OTULabelStyleEnum
from peyotl.utility import get_logger, get_config_setting, get_config_object


def gen_otu_dict(nex_obj, nexson_version=None):
    """Takes a NexSON object and returns a dict of
    otu_id -> otu_obj
    """
    if nexson_version is None:
        nexson_version = detect_nexson_version(nex_obj)
    if _is_by_id_hbf(nexson_version):
        otus = nex_obj['nexml']['otusById']
        if len(otus) > 1:
            d = {}
            for v in otus.values():
                d.update(v['otuById'])
            return d
        else:
            return otus.values()[0]['otuById']
    o_dict = {}
    for ob in nex_obj.get('otus', []):
        for o in ob.get('otu', []):
            oid = o['@id']
            o_dict[oid] = o
    return o_dict


def iter_tree(nex_obj):
    """Generator over each tree object in the NexSON object."""
    for tb in nex_obj.get('trees', []):
        for tree in tb.get('tree', []):
            yield tree


def iter_node(tree):
    """Generator over each node object in the tree object."""
    for nd in tree.get('nodeById', {}).items():
        yield nd


__all__ = ['utility',
           'api',
           'nexson_proxy',
           'nexson_syntax',
           'nexson_validation',
           'ott',
           'phylesystem',
           'sugar',
           'test',
           'utility',
           'external',
           'manip',
           'struct_diff',
           'evaluate_tree',
           ]
