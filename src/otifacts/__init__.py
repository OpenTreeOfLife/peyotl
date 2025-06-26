import codecs
import json
import os
from peyotl.utility.get_logger import get_logger

_LOG = get_logger(__name__)


def find_otifacts_json_filepaths(otifacts_dir):
    """Walks a top-level directory with the OTifacts structure and returns a list of 
    JSON filepaths for all of the non-excluded directories."""
    is_first = True
    fp_list = []
    for dirpath, dirname, filenames in os.walk(otifacts_dir):
        if is_first:
            is_first = False
            for skip in ['.git', 'references', 'scripts', 'env']:
                try:
                    dirname.remove(skip)
                except:
                    pass
        else:
            for filename in filenames:
                if filename.endswith('.json'):
                    path = os.path.join(dirpath, filename)
                    fp_list.append(path)
    return fp_list


def read_all_otifacts(otifacts_dir):
    """Reads all of the JSON files in the OTifacts directory and returns a dictionary that is the
    union of all of them.
    """
    union = {}
    for fp in find_otifacts_json_filepaths(otifacts_dir):
        with codecs.open(fp, 'rU', encoding='utf-8') as inp:
            try:
                obj = json.load(inp)
            except:
                _LOG.exception('Could not read JSON in "{}"'.format(fp))
                raise
            else:
                for k, v in obj.items():
                    if k in union:
                        m = 'Repeated id "{}". Second occurence in "{}"'.format(k, fp)
                        raise RuntimeError(m)
                    union[k] = v
    return union


def filter_otifacts_by_type(all_res, resource_type_value):
    # only complicated because you can have an 'inherits_from' rather than 'resource_type'
    rtype_and_par = {}
    unk_type = set()
    for k, v in all_res.items():
        rt = v.get('resource_type')
        if rt is None:
            rtype_and_par[k] = [None, v['inherits_from']]
            unk_type.add(k)
        else:
            rtype_and_par[k] = (rt, None)
    nunk = len(unk_type)
    while unk_type:
        to_check = unk_type
        unk_type = set()
        for k in to_check:
            rt_and_par = rtype_and_par[k]
            if rt_and_par[0] is None:
                par = rt_and_par[1]
                pt = rtype_and_par[par]
                if pt[0] is not None:
                    rt_and_par[0] = pt[0]
                else:
                    unk_type.add(k)
        nnunk = len(unk_type)
        if nnunk == nunk:
            raise RuntimeError("Infinite loop. Can't find resource types for : {}".format(unk_type))
        nunk = nnunk
    # No filter the resources
    retd = {}
    for k, rt_and_par in rtype_and_par.items():
        if rt_and_par[0] == resource_type_value:
            retd[k] = all_res[k]
    return retd

def partition_otifacts_by_root_element(res_dict):
    """Takes a dict mapping res ID to resource objects in OTifacts schema.
    Returns a dict mapping just "root" ID to dicts of res ID to object.
    """
    root_els = set()
    to_dict = {}
    moved = set()
    to_check = set()
    for key, res in res_dict.items():
        if res.get('inherits_from') is None:
            to_dict[key] = {key: res}
            root_els.add(key)
            moved.add(key)
        else:
            to_check.add(key)
    while to_check:
        ntc = set()
        for key in to_check:
            res = res_dict[key]
            par = res['inherits_from']
            par_dict = to_dict.get(par)
            if par_dict is not None:
                par_dict[key] = res
                to_dict[key] = par_dict
            else:
                ntc.add(key)
        if len(to_check) == len(ntc):
            raise RuntimeError("Infinite loop. Can't find parent for : {}".format(ntc))
        to_check = ntc
    ret = {}
    for el in root_els:
        ret[el] = to_dict[el]
    return ret
