#!/usr/bin/env python
from peyotl.nexson_syntax import iter_otu, write_as_json
from peyotl.api import APIWrapper
from peyotl.ott import OTT
from peyotl import get_logger
import sys
_LOG = get_logger('otu-label-comparison')
if len(sys.argv) != 2:
    sys.exit('expecting an output file path for the JSON mapping file')
outfn = sys.argv[1]
a = APIWrapper(phylesystem_api_kwargs={'get_from':'local'})
ott = OTT()
ott_id_to_names = ott.ott_id_to_names
orig2ott_name = {}

phylesys = a.phylesystem_api.phylesystem_obj
for sid, blob in phylesys.iter_study_objs():
    maps = []
    for otu_id, otu in iter_otu(blob):
        ott_id = otu.get('^ot:ottId')
        if ott_id is not None:
            try:
                names = ott_id_to_names[ott_id]
            except:
                _LOG.debug('Apparently deprecated ott_id="{o}" in study="{s}"'.format(o=ott_id, s=sid))
            else:
                if not isinstance(names, tuple):
                    names = (names, )
                maps.append((otu['^ot:originalLabel'], names))
    if maps:
        orig2ott_name[sid] = maps
write_as_json(orig2ott_name, outfn)
