#!/usr/bin/env python
from peyotl.api.wrapper import _WSWrapper, APIWrapper
import anyjson
from peyotl import get_logger
_LOG = get_logger(__name__)

class _TreemachineAPIWrapper(_WSWrapper):
    def __init__(self, domain):
        _WSWrapper.__init__(self, domain)
        self.prefix = '{d}/treemachine/ext/GoLS/graphdb'.format(d=self.domain)
    def getSyntheticTreeInfo(self):
        uri = '{p}/getDraftTreeID'.format(p=self.prefix)
        return self._post(uri)
    def getSourceTreesIDList(self):
        uri = '{p}/getSourceTreeIDs'.format(p=self.prefix)
        return self._post(uri)
    def  getSynthesisSourceList(self):
        uri = '{p}/ getSynthesisSourceList'.format(p=self.prefix)
        return self._post(uri)
    def getSourceTree(self, treeID, format='newick', nodeID=None, maxDepth=None):
        uri = '{p}/getSourceTree'.format(p=self.prefix)
        return self._get_tree(uri, treeID, format=format, nodeID=nodeID, maxDepth=maxDepth)
    def getSyntheticTree(self, treeID, format='newick', nodeID=None, maxDepth=None):
        uri = '{p}/getSyntheticTree'.format(p=self.prefix)
        return self._get_tree(uri, treeID, format=format, nodeID=nodeID, maxDepth=maxDepth)
    def _get_tree(self, uri, treeID, format='newick', nodeID=None, maxDepth=None):
        format_list = ['newick', 'arguson']
        if format.lower() not in format_list:
            raise ValueError('Tree "format" must be a value in {}'.format(repr(format_list)))
        data = {'treeID': treeID,
                'format': format}
        if nodeID is not None:
            data['subtreeNodeID'] = nodeID
        if maxDepth is not None:
            data['maxDepthArg'] = maxDepth
        return self._post(uri, data=anyjson.dumps(data))


def Treemachine(domains=None):
    return APIWrapper(domains=domains).treemachine