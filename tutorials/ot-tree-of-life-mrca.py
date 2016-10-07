#!/usr/bin/env python
"""Simple command-line tool for reporting information about the node in the synthetic tree of life
that is the most recent common ancestor of a set of OTT IDs.

This uses the API described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#mrca
"""
import sys


def fetch_and_write_mrca(id_list, details, subtree, induced_subtree, output, errstream):
    from peyotl.sugar import tree_of_life
    mrca_node = tree_of_life.mrca(ott_ids=id_list, wrap_response=True)
    assert tuple() == mrca_node.invalid_node_ids
    assert tuple() == mrca_node.node_ids_not_in_tree
    if mrca_node.invalid_ott_ids:
        errstream.write(
            'The following OTT IDs were not valid: {}\n'.format(' '.join([str(i) for i in mrca_node.invalid_ott_ids])))
    if mrca_node.ott_ids_not_in_tree:
        f = 'The following OTT IDs are valid identifiers, but not recovered in the synthetic estimate of the tree of life: {}\n'
        errstream.write(f.format(' '.join([str(i) for i in mrca_node.ott_ids_not_in_tree])))
    DOMAIN = 'https://tree.opentreeoflife.org'
    URL_PATH_FMT = 'opentree/argus/otol.draft.22@{i:d}'
    URL_FMT = DOMAIN + '/' + URL_PATH_FMT
    url = URL_FMT.format(i=mrca_node.node_id)
    errstream.write('The (unstable) UFL for seeing this node in the ToL is: {}\n'.format(url))
    errstream.write('The (unstable) ID of the MRCA node in the graph of life is: {}\n'.format(mrca_node.node_id))
    if mrca_node.is_taxon:
        errstream.write('The node in the Graph of Life corresponds to a taxon:\n')
        mrca_node.write_report(errstream)
    else:
        errstream.write(
            'The node in the Graph of Life does not correspond to a taxon.\nThe most recent ancestor which is also a named taxon in OTT is:\n')
        mrca_node.nearest_taxon.write_report(errstream)

    if details:
        # could call mrca_node.fetch_node_info()
        errstream.write(
            'Source(s) that support this node: {}\n'.format(' '.join([str(i) for i in mrca_node.synth_sources])))
        errstream.write('Is in the synthetic tree of life? {}\n'.format(mrca_node.in_synth_tree))
        errstream.write('Correspondences with other taxonomies: {}\n'.format(mrca_node.tax_source))
        errstream.write('Is in the graph of life? {}\n'.format(mrca_node.in_graph))
        errstream.write('# tips below this node = {}\n'.format(mrca_node.num_tips))
        errstream.write('# children of this node = {}\n'.format(mrca_node.num_synth_children))

    if subtree:
        # We could ask for this using: 
        #   newick = tree_of_life.subtree(node_id=mrca_node.node_id)['newick']
        # or we can ask the GoLNodeWrapper object to do the call (as shown below)
        try:
            newick = mrca_node.subtree_newick
        except Exception as x:
            errstream.write('Could not fetch the subtree. Error: {}\n'.format(str(x)))
        else:
            errstream.write('The newick representation of the subtree rooted at this node is:\n')
            output.write('{}\n'.format(newick))

    if induced_subtree:
        induced_newick = tree_of_life.induced_subtree(ott_ids=id_list)['subtree']
        errstream.write('The newick representation of the induced subtree rooted at this node is:\n')
        output.write('{}\n'.format(induced_newick))


def main(argv):
    """This function sets up a command-line option parser and then calls fetch_and_write_mrca
    to do all of the real work.
    """
    import argparse
    description = 'Uses Open Tree of Life web services to the MRCA for a set of OTT IDs.'
    parser = argparse.ArgumentParser(prog='ot-tree-of-life-mrca', description=description)
    parser.add_argument('ottid', nargs='*', type=int, help='OTT IDs')
    parser.add_argument('--subtree', action='store_true', default=False, required=False,
                        help='write a newick representation of the subtree rooted at this mrca')
    parser.add_argument('--induced-subtree', action='store_true', default=False, required=False,
                        help='write a newick representation of the topology of the requested taxa in the synthetic tree (the subtree pruned to just the queried taxa)')
    parser.add_argument('--details', action='store_true', default=False, required=False,
                        help='report more details about the mrca node')
    args = parser.parse_args(argv)
    id_list = args.ottid
    if not id_list:
        sys.stderr.write('No OTT IDs provided. Running a dummy query with 770302 770315\n')
        id_list = [770302, 770315]
    fetch_and_write_mrca(id_list, args.details, args.subtree, args.induced_subtree, sys.stdout, sys.stderr)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as x:
        sys.exit('{}\n'.format(str(x)))
