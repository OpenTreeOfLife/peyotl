#!/usr/bin/env python
'''Simple command-line tool for reporting information about the node in the synthetic tree of life
that is the most recent common ancestor of a set of OTT IDs.

This uses the API described at https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs#mrca
'''
import sys

def fetch_and_write_mrca(id_list, subtree, induced_subtree, output):
    from peyotl.sugar import tree_of_life
    mrca_node = tree_of_life.mrca(ott_ids=id_list, wrap_response=True)

    assert tuple() == mrca_node.invalid_node_ids
    assert tuple() == mrca_node.node_ids_not_in_tree
    if mrca_node.invalid_ott_ids:
        output.write('The following OTT IDs were not valid: {}\n'.format(' '.join([str(i) for i in mrca_node.invalid_ott_ids])))
    if mrca_node.ott_ids_not_in_tree:
        f = 'The following OTT IDs are valid identifiers, but not recovered in the synthetic estimate of the tree of life: {}\n'
        output.write(f.format(' '.join([str(i) for i in mrca_node.ott_ids_not_in_tree])))
    output.write('The (unstable) ID of the MRCA node in the graph of life is: {}\n'.format(mrca_node.node_id))
    if mrca_node.is_taxon:
        output.write('The node in the Graph of Life corresponds to a taxon:\n')
        mrca_node.write_report(output)
    else:
        output.write('The node in the Graph of Life does not correspond to a taxon.\nThe most recent ancestor which is also a named taxon in OTT is:\n')
        mrca_node.nearest_taxon.write_report(output)

    if subtree:
        # We could ask for this using: 
        #   newick = tree_of_life.subtree(node_id=mrca_node.node_id)['newick']
        # or we can ask the GoLNodeWrapper object to do the call (as shown below)
        try:
            newick = mrca_node.subtree_newick
        except Exception as x:
            sys.stdout.write('Could not fetch the subtree. Error: {}\n'.format(str(x)))
        else:
            output.write('The newick representation of the subtree rooted at this node is:\n{}\n'.format(newick))

    if induced_subtree:
        induced_newick = tree_of_life.induced_subtree(ott_ids=id_list)['subtree']
        output.write('The newick representation of the induced subtree rooted at this node is:\n{}\n'.format(induced_newick))


def main(argv):
    '''This function sets up a command-line option parser and then calls fetch_and_write_mrca
    to do all of the real work.
    '''
    import argparse
    description = 'Uses Open Tree of Life web services to the MRCA for a set of OTT IDs.'
    parser = argparse.ArgumentParser(prog='ot-tree-of-life-mrca', description=description)
    parser.add_argument('ottid', nargs='*', type=int, help='OTT IDs')
    parser.add_argument('--subtree', action='store_true', default=False, required=False)
    parser.add_argument('--induced-subtree', action='store_true', default=False, required=False)
    args = parser.parse_args(argv)
    id_list = args.ottid
    if not id_list:
        sys.stderr.write('No OTT IDs provided. Running a dummy query with 770302 770315\n')
        id_list = [770302, 770315]
    fetch_and_write_mrca(id_list, args.subtree, args.induced_subtree, sys.stdout)
    
if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception, x:
        raise
        sys.exit('{}\n'.format(str(x)))

