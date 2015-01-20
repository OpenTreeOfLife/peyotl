#!/usr/bin/env python
import pickle
import sys
import os
if __name__ == '__main__':
    from peyotl.ott import OTT
    picklefn = sys.argv[1]
    if os.path.exists(picklefn):
        sys.exit('{} already exists'.format(picklefn))
    ott = OTT()
    ncbi2ott = {}
    for ott_id, info in ott.ott_id_to_info.items():
        ncbi = info.get('ncbi')
        if ncbi is not None:
            assert ncbi not in ncbi2ott
            ncbi2ott[ncbi] = ott_id
    with open(picklefn, 'wb') as fo:
        pickle.dump(ncbi2ott, fo)
