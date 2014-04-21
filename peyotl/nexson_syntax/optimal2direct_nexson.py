#!/usr/bin/env python
'Optimal2DirectNexson class'
from peyotl.nexson_syntax.helper import NexsonConverter, \
                                        get_nexml_el, \
                                        DIRECT_HONEY_BADGERFISH
from peyotl.utility import get_logger
_LOG = get_logger(__name__)
class Optimal2DirectNexson(NexsonConverter):
    '''Conversion of the optimized (v 1.2) version of NexSON to
    the more direct (v 1.0) port of NeXML
    This is a dict-to-dict in-place conversion. No serialization is included.
    '''
    def __init__(self, conv_cfg):
        NexsonConverter.__init__(self, conv_cfg)

    def convert_otus(self, otusById, otusElementOrder):
        if self.pristine_if_invalid:
            raise NotImplementedError('pristine_if_invalid option is not supported yet')
        otu_group_list = []
        for oid in otusElementOrder:
            otu_group = otusById[oid]
            otu_group['@id'] = oid
            otu_list = []
            otu_by_id = otu_group['otuById']
            otu_id_list = otu_by_id.keys()
            otu_id_list.sort() # not necessary, but will give us a consistent order...
            for otu_id in otu_id_list:
                otu = otu_by_id[otu_id]
                otu['@id'] = otu_id
                otu_list.append(otu)
            otu_group['otu'] = otu_list
            if self.remove_old_structs:
                del otu_group['otuById']
            otu_group_list.append(otu_group)
        return otu_group_list

    def convert_tree(self, tree):
        if self.pristine_if_invalid:
            raise NotImplementedError('pristine_if_invalid option is not supported yet')
        nodeById = tree['nodeById']
        edgeBySourceId = tree['edgeBySourceId']
        root_node_id = tree['^ot:rootNodeId']
        node_list = []
        edge_list = []
        curr_node_id = root_node_id
        edge_stack = []
        node_set_written = set()
        edge_set_written = set()
        while True:
            curr_node = nodeById[curr_node_id]
            curr_node['@id'] = curr_node_id
            assert curr_node_id not in node_set_written
            node_set_written.add(curr_node_id)
            node_list.append(curr_node)
            sub_edge_dict = edgeBySourceId.get(curr_node_id)
            if sub_edge_dict:
                ks = sub_edge_dict.keys()
                ks.sort()
                sub_edge_list = [(ski, sub_edge_dict[ski]) for ski in ks]
                eid, edge = sub_edge_list[0]
                to_stack = sub_edge_list[-1:0:-1]
                edge_stack.extend(to_stack)
            else:
                curr_node['^ot:isLeaf'] = True
                if not edge_stack:
                    break
                eid, edge = edge_stack.pop(-1)
            edge['@id'] = eid
            edge_list.append(edge)
            assert eid not in edge_set_written
            edge_set_written.add(eid)
            curr_node_id = edge['@target']
        for n in nodeById.values():
            assert n['@id'] in node_set_written
        tree['node'] = node_list
        tree['edge'] = edge_list
        if self.remove_old_structs:
            del tree['nodeById']
            del tree['edgeBySourceId']
            del tree['^ot:rootNodeId']
        return tree

    def convert_trees(self, treesById, treesElementOrder):
        from peyotl.nexson_validation.helper import NexsonError

        if self.pristine_if_invalid:
            raise NotImplementedError('pristine_if_invalid option is not supported yet')
        trees_group_list = []
        tree_id_set = set()
        trees_id_set = set()
        for tgid in treesElementOrder:
            #_LOG.debug('tgid = ' + tgid)
            tree_group = treesById[tgid]
            if tgid in trees_id_set:
                raise NexsonError('Repeated trees element id "{}"'.format(tgid))
            trees_id_set.add(tgid)
            tree_group['@id'] = tgid
            treeElementOrder = tree_group['^ot:treeElementOrder']
            tree_list = []
            tree_by_id = tree_group['treeById']
            for tree_id in treeElementOrder:
                if tree_id in tree_id_set:
                    raise NexsonError('Repeated tree element id "{}"'.format(tree_id))
                tree_id_set.add(tree_id)
                tree = tree_by_id[tree_id]
                #_LOG.debug('pre-convert  tree(id={}).keys = {}'.format(tree_id, tree.keys()))
                self.convert_tree(tree)
                #_LOG.debug('post-convert tree(id={}).keys = {}'.format(tree_id, tree.keys()))
                tree['@id'] = tree_id
                tree_list.append(tree)
            tree_group['tree'] = tree_list
            if self.remove_old_structs:
                del tree_group['treeById']
                del tree_group['^ot:treeElementOrder']
            trees_group_list.append(tree_group)
        return trees_group_list

    def convert(self, obj):
        '''Takes a dict corresponding to the honeybadgerfish JSON blob of the 1.2.* type and
        converts it to DIRECT_HONEY_BADGERFISH version. The object is modified in place
        and returned.
        '''
        if self.pristine_if_invalid:
            raise NotImplementedError('pristine_if_invalid option is not supported yet')

        nex = get_nexml_el(obj)
        assert nex
        # Create the new objects as locals. This section should not
        #   mutate obj, so that if there is an exception the object
        #   is unchanged on the error exit
        otusById = nex['otusById']
        otusElementOrder = nex['^ot:otusElementOrder']
        otus = self.convert_otus(otusById, otusElementOrder)
        nex['otus'] = otus
        treesById = nex['treesById']
        treesElementOrder = nex['^ot:treesElementOrder']
        trees = self.convert_trees(treesById, treesElementOrder)
        # add the locals to the object
        nex['trees'] = trees
        nex['@nexml2json'] = str(DIRECT_HONEY_BADGERFISH)
        # Make the struct leaner
        if self.remove_old_structs:
            del nex['otusById']
            del nex['^ot:otusElementOrder']
            del nex['treesById']
            del nex['^ot:treesElementOrder']
        return obj
