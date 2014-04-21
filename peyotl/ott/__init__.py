#!/usr/bin/env python
from peyotl.utility import get_config, get_logger
import codecs
import os
_LOG = get_logger(__name__)
NONE_PAR = -1
class OTT(object):
    def __init__(self, ott_dir=None):
        if ott_dir is None:
            ott_dir = get_config('ott', 'parent')
        if ott_dir is None:
            raise ValueError('Either the ott_dir arg must be used or "parent" must exist in the "[ott]" section of your config (~/.peyotl/config by default)')
        self.ott_dir = ott_dir
        if not os.path.isdir(self.ott_dir):
            raise ValueError('"{}" is not a directory'.format(self.ott_dir))
        version = os.path.split(os.path.realpath(self.ott_dir))[-1][3:]
        taxonomy_file = os.path.join(self.ott_dir, 'taxonomy.tsv')
        if not os.path.isfile(taxonomy_file):
            raise ValueError('Expecting to find "{}" based on ott_dir ([ott] parent setting) of "{}"'.format(taxonomy_file, ott_dir))
        num_lines = 0

        id2par = {}  # UID to parent UID
        id2name = {} # UID to 'name' field
        id2uniq = {} # UID to 'uniqname' field
        uniq2id = {} # uniqname to UID
        id2info = {} # UID to {rank: ... silva: ..., ncbi: ... gbif:..., irmng : f}
                     # where the value for f is a key in flag_set_id2flag_set
        flag_set_id2flag_set = {}
        flag_set2flag_set_id = {}
        info_fields = set()
        sources = set()
        flag_set = set()
        f_set_id = 0
        info = {}
        with codecs.open(taxonomy_file, 'rU', encoding='utf-8') as tax_fo:
            it = iter(tax_fo)
            first_line = it.next()
            assert first_line == 'uid\t|\tparent_uid\t|\tname\t|\trank\t|\tsourceinfo\t|\tuniqname\t|\tflags\t|\t\n'
            life_line = it.next()
            root_split = life_line.split('\t|\t')
            uid = int(root_split[0])
            assert root_split[1] == ''
            name, rank, sourceinfo, uniqname, flags = root_split[2:7]
            assert name == 'life'
            assert root_split[7] == '\n'
            assert uid not in id2par
            id2par[uid] = NONE_PAR
            id2name[uid] = name
            if uniqname:
                id2uniq[uid] = uniqname
                assert uniqname not in uniq2id
                uniq2id[uniqname] = uid
            if sourceinfo:
                s_list = sourceinfo.split(',')
                for x in s_list:
                    src, sid = x.split(':')
                    try:
                        sid = int(sid)
                    except:
                        pass
                    sources.add(src)
                    info[src] = sid
            if flags:
                f_list = flags.split(',')
                if len(f_list) > 1:
                    f_list.sort()
                f_set = frozenset(f_list)
                for x in f_list:
                    flag_set.add(x)
                fsi = flag_set2flag_set_id.get(f_set)
                if fsi is None:
                    fsi = f_set_id
                    f_set_id += 1
                    flag_set_id2flag_set[fsi] = f_set
                info['f'] = fsi
            if info:
                id2info[uid] = info
                info = {}
            for rown in it:
                ls = rown.split('\t|\t')
                uid, par, name, rank, sourceinfo, uniqname, flags = ls[:7]
                if uniqname.startswith('environmental samples (') \
                    or uniqname.startswith('uncultured (') \
                    or uniqname.startswith('Incertae Sedis ('):
                    continue
                uid = int(uid)
                par = int(par)
                assert ls[7] == '\n'
                assert uid not in id2par
                if par not in id2par:
                    import sys; sys.exit(par)
                id2par[uid] = par
                id2name[uid] = name
                if uniqname:
                    id2uniq[uid] = uniqname
                    if uniqname in uniq2id:
                        _LOG.error('uniqname "{u}" used for OTT ID "{f:d}" and "{n:d}"'.format(
                            u=uniqname,
                            f=uniq2id[uniqname],
                            n=uid))
                    uniq2id[uniqname] = uid
                if sourceinfo:
                    s_list = sourceinfo.split(',')
                    for x in s_list:
                        src, sid = x.split(':')
                        try:
                            sid = int(sid)
                        except:
                            pass
                        sources.add(src)
                        info[src] = sid
                if flags:
                    f_list = flags.split(',')
                    if len(f_list) > 1:
                        f_list.sort()
                    f_set = frozenset(f_list)
                    for x in f_list:
                        flag_set.add(x)
                    fsi = flag_set2flag_set_id.get(f_set)
                    if fsi is None:
                        fsi = f_set_id
                        f_set_id += 1
                        flag_set_id2flag_set[fsi] = f_set
                    info['f'] = fsi
                if info:
                    id2info[uid] = info
                    info = {}

                num_lines += 1
        print num_lines
    def write_newick(self, out, taxon):
        pass
