#!/usr/bin/env python
'''
Small library for conducting operations over the
entire set of NexSON files in one or more phylesystem
repositories.

Typical usage:
################################################################################
from peyotl import phylesystem_studies

for file_path in phylesystem_studies('parent/of/phylesystem/repo'):
    print (file_path)
'''

from peyotl.utility import get_config, \
                           expand_path, \
                           get_logger
from peyotl.nexson_syntax import can_convert_nexson_forms, \
                                 convert_nexson_format, \
                                 detect_nexson_version, \
                                 get_ot_study_info_from_nexml, \
                                 write_as_json, \
                                 write_obj_as_nexml
def gen_otu_dict(nex_obj):
    '''Takes a NexSON object and returns a dict of
    otu_id -> otu_obj
    '''
    o_dict = {}
    for ob in nex_obj.get('otus', []):
        for o in ob.get('otu', []):
            oid = o['@id']
            o_dict[oid] = o
    return o_dict

def iter_tree(nex_obj):
    '''Generator over each tree object in the NexSON object.'''
    for tb in nex_obj.get('trees', []):
        for tree in tb.get('tree', []):
            yield tree

def iter_node(tree):
    '''Generator over each node object in the tree object.'''
    for nd in tree.get('node', []):
        yield nd
