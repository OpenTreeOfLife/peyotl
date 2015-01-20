#!/usr/bin/env python
import pickle
import sys
import os
if __name__ == '__main__':
    from peyotl.ott import OTT
    multimapping = set()
    picklefn = sys.argv[1]
    if os.path.exists(picklefn):
        sys.exit('{} already exists'.format(picklefn))
    ott = OTT()
    ncbi2ott = {}
    for ott_id, info in ott.ott_id_to_info.items():
        ncbi = info.get('ncbi')
        if ncbi is not None:
            if ncbi in ncbi2ott:
                prev = ncbi2ott[ncbi]
                if isinstance(prev, list):
                    prev.append(ott_id)
                else:
                    ncbi2ott[ncbi] = [prev, ott_id]
                    multimapping.add(ncbi)
            else:
                ncbi2ott[ncbi] = ott_id
    with open(picklefn, 'wb') as fo:
        pickle.dump(ncbi2ott, fo)
    if multimapping:
        sys.stderr.write('{i:d} ncbi IDs mapped to multiple OTT IDs\n'.format(i=len(multimapping)))
