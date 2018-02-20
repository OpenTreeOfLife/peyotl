#!/usr/bin/env python
from peyotl.nexson_syntax import (extract_tree_nexson,
                                  get_nexml_el,
                                  nexson_frag_write_newick)
from peyotl import OTULabelStyleEnum
from peyotl import write_as_json, read_as_json
from peyotl.ott import OTT
from peyotl.phylo.tree import SpikeTreeError
from peyotl.utility import propinquity_fn_to_study_tree
from peyotl import get_logger
from collections import defaultdict
import sys
import os

_SCRIPT_NAME = os.path.split(sys.argv[0])[-1]
_LOG = get_logger(__name__)
_VERBOSE = True


def debug(msg):
    if _VERBOSE:
        sys.stderr.write('{}: {}\n'.format(_SCRIPT_NAME, msg))


def error(msg):
    sys.stderr.write('{}: {}\n'.format(_SCRIPT_NAME, msg))


def find_tree_and_otus_in_nexson(nexson, tree_id):
    tl = extract_tree_nexson(nexson, tree_id)
    if (len(tl) != 1):
        #        sys.stderr.write('{}: len(tl) = {}\n'.format(tree_id,len(tl)))
        return None, None
    tree_id, tree, otus = tl[0]
    return tree, otus


class EmptyTreeError(Exception):
    pass


def _check_rev_dict(tree, ebt):
    """Verifyies that `ebt` is the inverse of the `edgeBySourceId` data member of `tree`"""
    ebs = defaultdict(dict)
    for edge in ebt.values():
        source_id = edge['@source']
        edge_id = edge['@id']
        ebs[source_id][edge_id] = edge
    assert ebs == tree['edgeBySourceId']


class NexsonTreeWrapper(object):
    def __init__(self, nexson, tree_id, log_obj=None):
        self.tree, self.otus = find_tree_and_otus_in_nexson(nexson, tree_id)
        if self.tree is None:
            raise KeyError('Tree "{}" was not found.'.format(tree_id))
        self._log_obj = log_obj
        self._edge_by_source = self.tree['edgeBySourceId']
        self._node_by_id = self.tree['nodeById']
        self._root_node_id = None
        self.root_node_id = self.tree['^ot:rootNodeId']
        assert self.root_node_id
        self._ingroup_node_id = self.tree.get('^ot:inGroupClade')
        for k, v in self._node_by_id.items():
            v['@id'] = k
        self._edge_by_target = self._create_edge_by_target()
        self.nodes_deleted, self.edges_deleted = [], []
        self._by_ott_id = None
        self.is_empty = False

    def get_root_node_id(self):
        return self._root_node_id

    def set_root_node_id(self, r):
        try:
            assert r
            assert r in self._edge_by_source
            assert r in self._node_by_id
        except:
            error('Illegal root node "{}"'.format(r))
            raise
        self._root_node_id = r

    root_node_id = property(get_root_node_id, set_root_node_id)

    def _create_edge_by_target(self):
        """creates a edge_by_target dict with the same edge objects as the edge_by_source.
        Also adds an '@id' field to each edge."""
        ebt = {}
        for edge_dict in self._edge_by_source.values():
            for edge_id, edge in edge_dict.items():
                target_id = edge['@target']
                edge['@id'] = edge_id
                assert target_id not in ebt
                ebt[target_id] = edge
        # _check_rev_dict(self._tree, ebt)
        return ebt

    def _clear_del_log(self):
        self.nodes_deleted = []
        self.edges_deleted = []

    def _log_deletions(self, key):
        if log_obj is not None:
            o = log_obj.setdefault(key, {'nodes': [], 'edges': []})
            o['nodes'].extend(self.nodes_deleted)
            o['edges'].extend(self.edges_deleted)
        self._clear_del_log()

    def _do_prune_to_ingroup(self):
        edge_to_del = self._edge_by_target.get(self._ingroup_node_id)
        if edge_to_del is None:
            return
        try:
            self.prune_edge_and_rootward(edge_to_del)
        finally:
            self._log_deletions('outgroup')

    def prune_to_ingroup(self):
        """Remove nodes and edges from tree if they are not the ingroup or a descendant of it."""
        # Prune to just the ingroup
        if not self._ingroup_node_id:
            _LOG.debug('No ingroup node was specified.')
            self._ingroup_node_id = self.root_node_id
        elif self._ingroup_node_id != self.root_node_id:
            self._do_prune_to_ingroup()
            self.root_node_id = self._ingroup_node_id
        else:
            _LOG.debug('Ingroup node is root.')
        return self.root_node_id

    def prune_edge_and_rootward(self, edge_to_del):
        while edge_to_del is not None:
            source_id, target_id = self._del_edge(edge_to_del)
            ebsd = self._edge_by_source.get(source_id)
            if ebsd:
                to_prune = list(ebsd.values())  # will modify ebsd in loop below, so shallow copy
                for edge in to_prune:
                    self.prune_edge_and_tipward(edge)
                assert source_id not in self._edge_by_source
            edge_to_del = self._edge_by_target.get(source_id)

    def prune_edge_and_tipward(self, edge):
        source_id, target_id = self._del_edge(edge)
        self.prune_clade(target_id)

    def prune_clade(self, node_id):
        """Prune `node_id` and the edges and nodes that are tipward of it.
        Caller must delete the edge to node_id."""
        to_del_nodes = [node_id]
        while bool(to_del_nodes):
            node_id = to_del_nodes.pop(0)
            self._flag_node_as_del_and_del_in_by_target(node_id)
            ebsd = self._edge_by_source.get(node_id)
            if ebsd is not None:
                child_edges = list(ebsd.values())
                to_del_nodes.extend([i['@target'] for i in child_edges])
                del self._edge_by_source[
                    node_id]  # deletes all of the edges out of this node (still held in edge_by_target til children are encountered)

    def _flag_node_as_del_and_del_in_by_target(self, node_id):
        """Flags a node as deleted, and removes it from the _edge_by_target (and parent's edge_by_source), if it is still found there.
        Does NOT remove the node's entries from self._edge_by_source."""
        self.nodes_deleted.append(node_id)
        etp = self._edge_by_target.get(node_id)
        if etp is not None:
            del self._edge_by_target[node_id]

    def _del_edge(self, edge_to_del):
        edge_id = edge_to_del['@id']
        target_id = edge_to_del['@target']
        source_id = edge_to_del['@source']
        del self._edge_by_target[target_id]
        ebsd = self._edge_by_source[source_id]
        del ebsd[edge_id]
        if not ebsd:
            del self._edge_by_source[source_id]
        self.edges_deleted.append(edge_id)
        return source_id, target_id

    def _del_tip(self, node_id):
        """Assumes that there is no entry in edge_by_source[node_id] to clean up."""
        self.nodes_deleted.append(node_id)
        etp = self._edge_by_target.get(node_id)
        assert etp is not None
        source_id, target_id = self._del_edge(etp)
        assert target_id == node_id
        return source_id

    def group_and_sort_leaves_by_ott_id(self):
        """returns a dict mapping ott_id to list of elements referring to leafs mapped
        to that ott_id. They keys will be ott_ids and None (for unmapped tips). The values
        are lists of tuples. Each tuple represents a different leaf and contains:
            (integer_for_of_is_examplar: -1 if the node is flagged by ^ot:isTaxonExemplar. 0 otherwise
            the leaf's node_id,
            the node object
            the otu object for the node
            )
        """
        ott_id_to_sortable_list = defaultdict(list)
        for node_id in self._edge_by_target.keys():
            node_obj = self._node_by_id[node_id]
            if node_id in self._edge_by_source:
                continue
            otu_id = node_obj['@otu']
            otu_obj = self.otus[otu_id]
            ott_id = otu_obj.get('^ot:ottId')
            is_exemplar = node_obj.get('^ot:isTaxonExemplar', False)
            int_is_exemplar = 0
            if is_exemplar:
                int_is_exemplar = -1  # to sort to the front of the list
            sortable_el = (int_is_exemplar, node_id, node_obj, otu_obj)
            ott_id_to_sortable_list[ott_id].append(sortable_el)
        for v in ott_id_to_sortable_list.values():
            v.sort()
        return ott_id_to_sortable_list

    @property
    def by_ott_id(self):
        if self._by_ott_id is None:
            self._by_ott_id = self.group_and_sort_leaves_by_ott_id()
        return self._by_ott_id

    def prune_unmapped_leaves(self):
        # Leaf nodes with no OTT ID at all...
        if None in self.by_ott_id:
            self.prune_tip_in_sortable_list(self.by_ott_id[None], 'unmapped_otu')
            del self.by_ott_id[None]

    def prune_tip_in_sortable_list(self, sortable_list, reason):
        try:
            par_to_check = set()
            for sortable_el in sortable_list:
                node_id = sortable_el[1]
                par_to_check.add(self._del_tip(node_id))
                self.nodes_deleted.append(node_id)
        finally:
            self._log_deletions(reason)
        self.prune_if_deg_too_low(par_to_check)

    prune_ott_problem_leaves = prune_tip_in_sortable_list

    def prune_if_deg_too_low(self, ind_nd_id_list):
        try:
            orphaned_root = None
            while bool(ind_nd_id_list):
                next_ind_nd_id_list = set()
                for nd_id in ind_nd_id_list:
                    out_edges = self._edge_by_source.get(nd_id)
                    if out_edges is None:
                        out_degree = 0
                    else:
                        out_degree = len(out_edges)
                    if out_degree < 2:
                        to_par = self._edge_by_target.get(nd_id)
                        if to_par:
                            par = to_par['@source']
                            next_ind_nd_id_list.add(par)
                            if out_degree == 1:
                                out_edge = out_edges.values()[0]
                                self.suppress_deg_one_node(to_par, nd_id, out_edge)
                            else:
                                self._del_tip(nd_id)
                            if nd_id in next_ind_nd_id_list:
                                next_ind_nd_id_list.remove(nd_id)
                        else:
                            assert (orphaned_root is None) or (orphaned_root == nd_id)
                            orphaned_root = nd_id
                ind_nd_id_list = next_ind_nd_id_list
            if orphaned_root is not None:
                new_root = self.prune_deg_one_root(orphaned_root)
                if self._log_obj is not None:
                    self._log_obj['revised_ingroup_node'] = new_root
                self.root_node_id, self._ingroup_node_id = new_root, new_root
        finally:
            self._log_deletions('became_trivial')

    def suppress_deg_one_node(self, to_par_edge, nd_id, to_child_edge):
        """Deletes to_par_edge and nd_id. To be used when nd_id is an out-degree= 1 node"""
        # circumvent the node with nd_id
        to_child_edge_id = to_child_edge['@id']
        par = to_par_edge['@source']
        self._edge_by_source[par][to_child_edge_id] = to_child_edge
        to_child_edge['@source'] = par
        # make it a tip...
        del self._edge_by_source[nd_id]
        # delete it
        self._del_tip(nd_id)

    def prune_deg_one_root(self, new_root):
        while True:
            ebs_el = self._edge_by_source.get(new_root)
            if ebs_el is None:
                self.is_empty = True
                raise EmptyTreeError()
            if len(ebs_el) > 1:
                return new_root
            edge = ebs_el.values()[0]
            new_root = edge['@target']
            self._del_tip(new_root)
    def prune_ott_problem_leaves_by_id(self, ott_id, reason):
        self.prune_ott_problem_leaves(self.by_ott_id[ott_id], reason)
        del self.by_ott_id[ott_id]

    def prune_tree_for_supertree(self,
                                 ott,
                                 to_prune_fsi_set,
                                 root_ott_id,
                                 taxonomy_treefile=None,
                                 id_to_other_prune_reason=None):
        """
        `to_prune_fsi_set` is a set of flag indices to be pruned.
        """
        if id_to_other_prune_reason is None:
            id_to_other_prune_reason = {}
        self.prune_to_ingroup()
        self.prune_unmapped_leaves()
        other_pruned = set()
        if id_to_other_prune_reason:
            id2p = set(id_to_other_prune_reason.keys()).intersection(set(self.by_ott_id.keys()))
            for ott_id in id2p:
                reason = id_to_other_prune_reason[ott_id]
                self.prune_ott_problem_leaves_by_id(ott_id, reason)
        # Check the stored OTT Ids against the current version of OTT
        mapped, unrecog, forward2unrecog, pruned, above_root, old2new = ott.map_ott_ids(self.by_ott_id.keys(),
                                                                                        to_prune_fsi_set, root_ott_id)
        for ott_id in unrecog:
            self.prune_ott_problem_leaves_by_id(ott_id, 'unrecognized_ott_id')
        for ott_id in forward2unrecog:
            self.prune_ott_problem_leaves_by_id(ott_id, 'forwarded_to_unrecognized_ott_id')
        for ott_id in pruned:
            self.prune_ott_problem_leaves_by_id(ott_id, 'flagged')
        for ott_id in above_root:
            self.prune_ott_problem_leaves_by_id(ott_id, 'above_root')
        for old_id, new_id in old2new.items():
            old_node_list = self.by_ott_id[old_id]
            del self.by_ott_id[old_id]
            if new_id in self.by_ott_id:
                v = self.by_ott_id[new_id]
                v.extend(old_node_list)
                v.sort() # I think only the last step requires sorting (NEED to check that,
                         # If so, we could move this sort to that point to avoid multiple sortings.
            else:
                self.by_ott_id[new_id] = old_node_list
            for sortable_el in old_node_list:
                otu = sortable_el[3]
                assert otu['^ot:ottId'] == old_id
                otu['^ot:ottId'] = new_id
                assert '^ot:ottTaxonName' in otu
                otu['^ot:ottTaxonName'] = ott.get_name(new_id)
        lost_tips = set(unrecog)
        lost_tips.update(forward2unrecog)
        lost_tips.update(pruned)
        lost_tips.update(other_pruned)
        # Get the induced tree...
        assert self.root_node_id
        try:
            ott_tree = ott.induced_tree(mapped, create_monotypic_nodes=True)
        except SpikeTreeError:
            error('SpikeTreeError from mapped ott_id list = {}'.format(', '.join([str(i) for i in mapped])))
            raise EmptyTreeError()
        if taxonomy_treefile is not None:
            with codecs.open(taxonomy_treefile, 'w', encoding='utf-8') as tto:
                ott_tree.write_newick(tto)
        # ... so that we can look for leaves mapped to ancestors of other leaves
        taxon_contains_other_ott_ids = []
        to_retain = []
        for ott_id in self.by_ott_id:
            if ott_id in lost_tips:
                continue
            n = old2new.get(ott_id)
            if n is None:
                n = ott_id
            nd = ott_tree.find_node(n)
            assert nd is not None
            if nd.children:
                # nd must be an internal node.
                #   given that the descendants of this node are mapped in a more specific
                #   way, we will prune this ott_id from the tree
                taxon_contains_other_ott_ids.append(ott_id)
            else:
                to_retain.append(ott_id)

        for ott_id in taxon_contains_other_ott_ids:
            self.prune_ott_problem_leaves_by_id(ott_id, 'mapped_to_taxon_containing_other_mapped_tips')
        # finally, we walk through any ott_id's mapped to multiple nodes
        for ott_id in to_retain:
            nm = self.by_ott_id[ott_id]
            if len(nm) > 1:
                el = nm.pop(0)
                reason = 'replaced_by_exemplar_node' if (el[0] == -1) else 'replaced_by_arbitrary_node'
                self.prune_ott_problem_leaves_by_id(ott_id, reason)
        return self


if __name__ == '__main__':
    import argparse
    import codecs
    import sys
    import os

    description = ''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('nexson',
                        nargs='*',
                        type=str,
                        help='nexson files with the name pattern studyID@treeID.json')
    parser.add_argument('--input-dir',
                        default=None,
                        type=str,
                        required=False,
                        help='a directory to prepend to the nexson filename or tag')
    parser.add_argument('--nexson-file-tags',
                        default=None,
                        type=str,
                        required=False,
                        help='a filepath to a file that holds the studyID@treeID "tag" for the inputs, one per line. ".json" will be appended to create the filenames.')
    parser.add_argument('--ott-dir',
                        default=None,
                        type=str,
                        required=True,
                        help='directory containing ott files (e.g "taxonomy.tsv")')
    parser.add_argument('--out-dir',
                        default=None,
                        type=str,
                        required=True,
                        help='Output directory for the newick files.')
    parser.add_argument('--ott-prune-flags',
                        default=None,
                        type=str,
                        required=False,
                        help='Optional comma-separated list of flags to prune. If omitted, the treemachine flags are used.')
    parser.add_argument('--ott-prune-nonflagged-json',
                        default=None,
                        type=str,
                        help='Optional JSON file that encodes and object that maps a string describing a reason to prune to a list of OTT Ids to prune')
    parser.add_argument('--root',
                        default=None,
                        type=int,
                        required=False,
                        help='Optional taxonomy root argument.')
    parser.add_argument('--input-files-list',
                        default=None,
                        type=str,
                        required=False,
                        help='A list of input NexSON filenames.')
    args = parser.parse_args(sys.argv[1:])
    ott_dir, out_dir, root = args.ott_dir, args.out_dir, args.root
    to_prune_for_reasons = {}
    nonflagged_json_fn = args.ott_prune_nonflagged_json
    if nonflagged_json_fn is not None:
        try:
            nonflagged_blob = read_as_json(nonflagged_json_fn)
        except:
            nonflagged_blob = None
        if nonflagged_blob:
            for reason, id_list in nonflagged_blob.items():
                for ott_id in id_list:
                    to_prune_for_reasons[ott_id] = reason
    flags_str = args.ott_prune_flags
    try:
        assert os.path.isdir(args.ott_dir)
    except:
        error('Expecting ott-dir argument to be a directory. Got "{}"'.format(args.ott_dir))
        sys.exit(1)
    if args.nexson:
        inp_files = list(args.nexson)
    else:
        if args.nexson_file_tags:
            with open(os.path.expanduser(args.nexson_file_tags), 'rU') as tf:
                inp_files = ['{}.json'.format(i.strip()) for i in tf if i.strip()]
        elif args.input_files_list:
            with open(os.path.expanduser(args.input_files_list), 'rU') as tf:
                inp_files = [i.strip() for i in tf if i.strip()]
        else:
            error(
                'nexson file must be specified as a positional argument or via the --nexson-file-tags or --input-files-list argument.')
            sys.exit(1)
    if not inp_files:
        error('No input files specified.')
    in_dir = args.input_dir
    if in_dir:
        in_dir = os.path.expanduser(in_dir)
        inp_files = [os.path.join(in_dir, i) for i in inp_files]
    if flags_str is None:
        flags = OTT.TREEMACHINE_SUPPRESS_FLAGS
    else:
        flags = flags_str.split(',')
    ott = OTT(ott_dir=args.ott_dir)
    to_prune_fsi_set = ott.convert_flag_string_set_to_union(flags)
    for inp in inp_files:
        _LOG.debug('{}'.format(inp))
        log_obj = {}
        inp_fn = os.path.split(inp)[-1]
        study_tree = '.'.join(inp_fn.split('.')[:-1])  # strip extension
        study_id, tree_id = propinquity_fn_to_study_tree(inp_fn)
        nexson_blob = read_as_json(inp)
        ntw = NexsonTreeWrapper(nexson_blob, tree_id, log_obj=log_obj)
        assert ntw.root_node_id
        taxonomy_treefile = os.path.join(args.out_dir, study_tree + '-taxonomy.tre')
        try:
            ntw.prune_tree_for_supertree(ott=ott,
                                         to_prune_fsi_set=to_prune_fsi_set,
                                         root_ott_id=root,
                                         taxonomy_treefile=taxonomy_treefile,
                                         id_to_other_prune_reason=to_prune_for_reasons)
        except EmptyTreeError:
            log_obj['EMPTY_TREE'] = True
        out_log = os.path.join(args.out_dir, study_tree + '.json')
        write_as_json(log_obj, out_log)
        newick_fp = os.path.join(args.out_dir, study_tree + '.tre')


        def compose_label(nodeid, node, otu):
            try:
                return '_'.join([otu['^ot:ottTaxonName'], str(node['@id']), 'ott' + str(otu['^ot:ottId'])])
            except:
                # internal nodes may lack otu's but we still want the node Ids
                return '_{}_'.format(str(node['@id']))


        with codecs.open(newick_fp, 'w', encoding='utf-8') as outp:
            if not ntw.is_empty:
                nexson_frag_write_newick(outp,
                                         ntw._edge_by_source,
                                         ntw._node_by_id,
                                         ntw.otus,
                                         label_key=compose_label,
                                         leaf_labels=None,
                                         root_id=ntw.root_node_id,
                                         ingroup_id=None,
                                         bracket_ingroup=False,
                                         with_edge_lengths=False)
                outp.write('\n')
