#!/usr/bin/env python
from peyotl.utility import get_config_object, get_logger
import pickle
import codecs
import os
_LOG = get_logger(__name__)
NONE_PAR = -1

class _TransitionalNode(object):
    def __init__(self, par=None):
        self.par = par
        self.children = None
        self.preorder_number = None
        if par is not None:
            par.add_child(self)
    def add_child(self, c):
        if self.children is None:
            self.children = [c]
        else:
            self.children.append(c)
    def number_tree(self, n):
        self.preorder_number = n
        if self.children is None:
            return n + 1
        n += 1
        for c in self.children:
            n = c.number_tree(n)
        return n
    def fill_preorder2tuples(self, r_sib_pn, preorder2tuples):
        ppn = self.par.preorder_number
        pn = self.preorder_number
        if self.children is None:
            t = (ppn, r_sib_pn)
        else:
            curr_c = self.children[0]
            left_child_pn = curr_c.preorder_number
            for r_sib in self.children[1:]:
                right_pn = r_sib.preorder_number
                curr_c.fill_preorder2tuples(right_pn, preorder2tuples)
                curr_c = r_sib
            curr_c.fill_preorder2tuples(None, preorder2tuples)
            right_child_pn = curr_c.preorder_number
            t = (ppn, r_sib_pn, left_child_pn, right_child_pn)
        assert pn not in preorder2tuples
        preorder2tuples[pn] = t

_CACHES = {'ottid2parentottid': ('ottId2parentOttId', 'ott ID-> parent\'s ott ID. root maps to -1', ),
           'ottid2preorder': ('ottID2preorder', 'ott ID -> preorder #', ),
           'preorder2ottid': ('preorder2ottID', 'preorder # -> ott ID', ),
           'ottid2uniq': ('ottID2uniq', 'ott ID -> uniqname for those IDs that have a uniqname field', ),
           'uniq2ottid': ('uniq2ottID', 'uniqname -> ott ID for those IDs that have a uniqname', ),
           'name2ottid': ('name2ottID', 'maps a taxon name -> ott ID ', ),
           'ottid2names': ('ottID2names', 'ottID to a name or list/tuple of names', ),
           'preorder2tuple': ('preorder2tuple', '''preorder # to a node definition
Each node definition is a tuple of preorder numbers:
    leaves will be: (parent, next_sib)
    internals will be: (parent, next_sib, first_child, last_child)
if a node is the last child of its parent, next_sib will be None
also in the map is 'root' -> root preorder number
''', ), }
class OTT(object):
    def __init__(self, ott_dir=None, **kwargs):
        self._config = get_config_object(None, **kwargs)
        if ott_dir is None:
            ott_dir = self._config.get_config_setting('ott', 'parent')
        if ott_dir is None:
            raise ValueError('Either the ott_dir arg must be used or "parent" must exist in '\
                             'the "[ott]" section of your config (~/.peyotl/config by default)')
        self.ott_dir = ott_dir
        if not os.path.isdir(self.ott_dir):
            raise ValueError('"{}" is not a directory'.format(self.ott_dir))
        self.skip_prefixes = ('environmental samples (', 'uncultured (', 'Incertae Sedis (')
        self._ott_id_to_names = None
        self._ott_id2par_ott_id = None
        self._version = None
    @property
    def version(self):
        if self._version is None:
            self._version = codecs.open(os.path.join(self.ott_dir, 'version.txt'), 'rU', encoding='utf-8').read().strip()
        return self._version
    @property
    def taxonomy_filepath(self):
        return os.path.abspath(os.path.join(self.ott_dir, 'taxonomy.tsv'))
    @property
    def synonyms_filepath(self):
        return os.path.abspath(os.path.join(self.ott_dir, 'synonyms.tsv'))
    @property
    def ott_id2par_ott_id(self):
        if self._ott_id2par_ott_id is None:
            fp = self.make('ottid2parentottid')
            self._ott_id2par_ott_id = self._load_cache_filepath(fp)
        return self._ott_id2par_ott_id

    def make(self, target):
        tl = target.lower()
        if tl not in _CACHES:
            raise ValueError('target "{t}" not understood. Must be one of: {a}', format(t=target,
                                                                                        a='\n  '.join(_CACHES.keys())))
        info = _CACHES[tl]
        fn = info[0] + '.pickle'
        fp = os.path.join(self.ott_dir, fn)
        need_build = False
        if not os.path.exists(fp):
            need_build = True
        else:
            taxonomy_file = self.taxonomy_filepath
            if not os.path.exists(taxonomy_file):
                raise RuntimeError('taxonomy not found at "{}"'.format(taxonomy_file))
            if os.path.getmtime(fp) < os.path.getmtime(taxonomy_file):
                need_build = True
            elif tl in ['name2ottid', 'ottid2names']: #TODO, make sure that these are the only files needing synonyms.
                if os.path.getmtime(fp) < os.path.getmtime(self.synonyms_filepath):
                    need_build = True
        if need_build:
            _LOG.debug('building "{}"'.format(fp))
            self.create_caches(out_dir=self.ott_dir)
        else:
            _LOG.debug('"{}" up to date.'.format(fp))
        return fp
    def _load_pickled(self, fn):
        fp = os.path.join(self.ott_dir, fn)
        return self._load_cache_filepath(fp)
    def _load_cache_filepath(self, fp):
        return pickle.load(open(fp, 'rb'))
    @property
    def ott_id_to_names(self):
        if self._ott_id_to_names is None:
            self._ott_id_to_names = self._load_pickled('ottID2names')
        return self._ott_id_to_names
    def create_caches(self, out_dir=None):
        try:
            self.create_pickle_files(out_dir=out_dir)
        except:
            raise # TODO, clean up
    def create_pickle_files(self, out_dir=None): #pylint: disable=R0914,R0915
        '''
           preorder2tuple maps a preorder number to a node definition. 
           ottID2preorder maps every OTT ID in taxonomy.tsv to a preorder #
        'ottID2preorder'
        'ottID2preorder'
        'preorder2ottID'
        'ottID2uniq'
        'uniq2ottID'
        'name2ottID'
        'ottID2names'
        'ottId2parentOttId'
        'preorder2tuple'
        '''
        if out_dir is None:
            out_dir = self.ott_dir
        taxonomy_file = self.taxonomy_filepath
        if not os.path.isfile(taxonomy_file):
            raise ValueError('Expecting to find "{}" based on ott_dir of "{}"'.format(taxonomy_file, self.ott_dir))
        num_lines = 0
        _LOG.debug('Reading "{f}"...'.format(f=taxonomy_file))
        id2par = {}  # UID to parent UID
        id2name = {} # UID to 'name' field
        id2uniq = {} # UID to 'uniqname' field
        uniq2id = {} # uniqname to UID
        id2info = {} # UID to {rank: ... silva: ..., ncbi: ... gbif:..., irmng : f}
                     # where the value for f is a key in flag_set_id2flag_set
        flag_set_id2flag_set = {}
        flag_set2flag_set_id = {}
        sources = set()
        flag_set = set()
        f_set_id = 0
        info = {}
        root_ott_id = None
        with codecs.open(taxonomy_file, 'r', encoding='utf-8') as tax_fo:
            it = iter(tax_fo)
            first_line = it.next()
            assert first_line == 'uid\t|\tparent_uid\t|\tname\t|\trank\t|\tsourceinfo\t|\tuniqname\t|\tflags\t|\t\n'
            life_line = it.next()
            root_split = life_line.split('\t|\t')
            uid = int(root_split[0])
            root_ott_id = uid
            assert root_split[1] == ''
            name, rank, sourceinfo, uniqname, flags = root_split[2:7] #pylint: disable=W0612
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
                skip = False
                for p in self.skip_prefixes:
                    if uniqname.startswith(p):
                        skip = True
                        break
                if skip:
                    continue
                uid = int(uid)
                par = int(par)
                assert ls[7] == '\n'
                assert uid not in id2par
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
                if num_lines % 100000 == 0:
                    _LOG.debug('read {n:d} lines...'.format(n=num_lines))
        _LOG.debug('read taxonomy file. total of {n:d} lines.'.format(n=num_lines))
        _write_pickle(out_dir, 'ottId2parentOttId', id2par)
        synonyms_file = self.synonyms_filepath
        _LOG.debug('Reading "{f}"...'.format(f=synonyms_file))
        if not os.path.isfile(synonyms_file):
            raise ValueError('Expecting to find "{}" based on ott_dir of "{}"'.format(synonyms_file, self.ott_dir))
        num_lines = 0
        with codecs.open(synonyms_file, 'r', encoding='utf-8') as syn_fo:
            it = iter(syn_fo)
            first_line = it.next()
            assert first_line == 'name\t|\tuid\t|\ttype\t|\tuniqname\t|\t\n'
            for rown in it:
                ls = rown.split('\t|\t')
                name, ott_id = ls[0], ls[1]
                ott_id = int(ott_id)
                if ott_id in id2name:
                    n = id2name[ott_id]
                    if isinstance(n, list):
                        n.append(name)
                    else:
                        id2name[ott_id] = [n, name]
                else:
                    _f = u'synonym "{n}" maps to an ott_id ({u}) that was not in the taxonomy!'
                    _m = _f.format(n=name, u=ott_id)
                    _LOG.debug(_m)
                num_lines += 1
                if num_lines % 100000 == 0:
                    _LOG.debug('read {n:d} lines...'.format(n=num_lines))
        _LOG.debug('read synonyms file. total of {n:d} lines.'.format(n=num_lines))
        _LOG.debug('normalizing id2name dict. {s:d} entries'.format(s=len(id2name)))
        _swap = {}
        for k, v in id2name.items():
            if isinstance(v, list):
                v = tuple(v)
            _swap[k] = v
        id2name = _swap
        _LOG.debug('inverting id2name dict. {s:d} entries'.format(s=len(id2name)))
        name2id = {}
        for ott_id, v in id2name.items():
            if not isinstance(v, tuple):
                v = [v]
            for el in v:
                prev = name2id.get(el)
                if prev is None:
                    name2id[el] = ott_id
                elif isinstance(prev, list):
                    prev.append(ott_id)
                else:
                    name2id[el] = [prev, ott_id]
        _LOG.debug('normalizing name2id dict. {s:d} entries'.format(s=len(name2id)))
        _swap = {}
        for k, v in name2id.items():
            if isinstance(v, list):
                v = tuple(v)
            _swap[k] = v
        name2id = _swap
        _LOG.debug('Making heavy tree')
        tt = make_tree_from_taxonomy(id2par)
        _LOG.debug('preorder numbering nodes')
        root = tt[root_ott_id]
        root.number_tree(0)
        _LOG.debug('creating ott_id <--> preorder maps')
        ott_id2preorder = {}
        preorder2ott_id = {}
        for ott_id, node in tt.items():
            ott_id2preorder[ott_id] = node.preorder_number
            preorder2ott_id[node.preorder_number] = ott_id
        ott_id2preorder['root_ott_id'] = root_ott_id
        ott_id2preorder['root'] = root.preorder_number
        preorder2ott_id['root'] = root_ott_id
        preorder2ott_id['root_preorder'] = root.preorder_number

        _write_pickle(out_dir, 'ottID2preorder', ott_id2preorder)
        _write_pickle(out_dir, 'preorder2ottID', preorder2ott_id)
        _write_pickle(out_dir, 'ottID2uniq', id2uniq)
        _write_pickle(out_dir, 'uniq2ottID', uniq2id)
        _write_pickle(out_dir, 'name2ottID', name2id)
        _write_pickle(out_dir, 'ottID2names', id2name)

        _LOG.debug('creating tree representation with preorder # to tuples')
        preorder2tuples = {}
        root.par = _TransitionalNode() # fake parent of root
        root.par.preorder_number = None
        root.fill_preorder2tuples(None, preorder2tuples)
        preorder2tuples['root'] = root.preorder_number
        _write_pickle(out_dir, 'preorder2tuple', preorder2tuples)

    def write_newick(self, out, taxon):
        pass
    def get_lineage(self, ott_id):
        curr = ott_id
        lineage = [curr]
        i2pi = self.ott_id2par_ott_id
        n = i2pi.get(curr)
        while n is not None and n != NONE_PAR:
            lineage.append(n)
            n = i2pi.get(n)
        return lineage

def _write_pickle(directory, fn, obj):
    fp = os.path.join(directory, fn + '.pickle')
    _LOG.debug('Creating "{p}"'.format(p=fp))
    with open(fp, 'wb') as fo:
        pickle.dump(obj, fo)

def _generate_parent(id2par, par_ott_id, ott2transitional):
    par = ott2transitional.get(par_ott_id)
    if par is not None:
        return par
    if par_ott_id == NONE_PAR:
        return None
    gp_id = id2par[par_ott_id]
    gp = ott2transitional.get(gp_id)
    if gp is None:
        gp = _generate_parent(id2par, gp_id, ott2transitional)
        if gp is None:
            root = _TransitionalNode()
            ott2transitional[gp_id] = root
            return root
    par = _TransitionalNode(gp)
    ott2transitional[par_ott_id] = par
    return par

def make_tree_from_taxonomy(id2par):
    ott2transitional = {}
    for ott_id, par_ott_id in id2par.items():
        par = _generate_parent(id2par, par_ott_id, ott2transitional)
        nd = _TransitionalNode(par=par)
        ott2transitional[ott_id] = nd
    return ott2transitional
if __name__ == '__main__':
    o = OTT()
    print len(o.ott_id2par_ott_id), 'ott IDs'
    print 'call'
    print o.get_lineage(5341349)

