#!/usr/bin/env python
from __future__ import absolute_import, print_function, division
from peyotl.phylo.entities import OTULabelStyleEnum
from peyotl.nexson_syntax import quote_newick_name
from peyotl.phylo.tree import create_tree_from_id2par, create_anc_lineage_from_id2par
from peyotl.utility.str_util import is_str_type
from peyotl.utility import get_config_object, get_logger
from collections import defaultdict
import pickle
import codecs
import os
_LOG = get_logger(__name__)
NONE_PAR = None

_PICKLE_AS_JSON = False
if _PICKLE_AS_JSON:
    from peyotl.utility.input_output import read_as_json, write_as_json

_TREEMACHINE_PRUNE_FLAGS = set(['major_rank_conflict',
                                'major_rank_conflict_direct',
                                'major_rank_conflict_inherited',
                                'environmental',
                                'unclassified_inherited',
                                'unclassified_direct',
                                'viral',
                                'nootu',
                                'barren',
                                'not_otu',
                                'incertae_sedis',
                                'incertae_sedis_direct',
                                'incertae_sedis_inherited',
                                'extinct_inherited',
                                'extinct_direct',
                                'hidden',
                                'unclassified',
                                'tattered'])

class OTTFlagUnion(object):
    def __init__(self, ott, flag_set):
        self._flag_set_keys = ott.convert_flag_string_set_to_flag_set_keys(flag_set)
    def keys(self):
        return set(self._flag_set_keys)


def write_newick_ott(out,
                     ott,
                     ott_id2children,
                     root_ott_id,
                     label_style,
                     prune_flags,
                     create_log_dict=False):
    '''`out` is an output stream
    `ott` is an OTT instance used for translating labels
    `ott_id2children` is a dict mapping an OTT ID to the IDs of its children
    `root_ott_id` is the root of the subtree to write.
    `label_style` is a facet of OTULabelStyleEnum
    `prune_flags` is a set strings (flags) or OTTFlagUnion instance or None
    if `create_log_dict` is True, a dict will be returned that contains statistics
        about the pruning.
    '''
    flags_to_prune_list = list(prune_flags) if prune_flags else []
    flags_to_prune_set = frozenset(flags_to_prune_list)
    pfd = {}
    # create to_prune_fsi_set a set of flag set indices to prune...
    if flags_to_prune_list:
        if not isinstance(prune_flags, OTTFlagUnion):
            to_prune_fsi_set = ott.convert_flag_string_set_to_union(prune_flags)
    else:
        to_prune_fsi_set = None

    log_dict = None
    if create_log_dict:
        log_dict = {}
        log_dict['version'] = ott.version
        log_dict['flags_to_prune'] = flags_to_prune_list
        fsi_to_str_flag_set = {}
        for k, v in dict(ott.flag_set_id_to_flag_set).items():
            fsi_to_str_flag_set[k] = frozenset(list(v))
        if to_prune_fsi_set:
            pfd = {}
            for f in to_prune_fsi_set.keys():
                s = fsi_to_str_flag_set[f]
                str_flag_intersection = flags_to_prune_set.intersection(s)
                pfd[f] = list(str_flag_intersection)
                pfd[f].sort()
        #log_dict['prune_flags_d'] = d
        #log_dict['pfd'] = pfd
        pruned_dict = {}
    num_tips = 0
    num_pruned_anc_nodes = 0
    num_nodes = 0
    num_monotypic_nodes = 0
    if to_prune_fsi_set and ott.has_flag_set_key_intersection(root_ott_id, to_prune_fsi_set):
        # entire taxonomy is pruned off
        if log_dict is not None:
            fsi = ott.get_flag_set_key(root_ott_id)
            pruned_dict[fsi] = {'': [root_ott_id]}
        num_pruned_anc_nodes += 1
    else:
        stack = [root_ott_id]
        first_children = set(stack)
        last_children = set()
        while stack:
            ott_id = stack.pop()
            if isinstance(ott_id, tuple):
                ott_id = ott_id[0]
            else:
                num_nodes += 1
                children = ott_id2children[ott_id]
                if to_prune_fsi_set is not None:
                    c = []
                    for child_id in children:
                        if ott.has_flag_set_key_intersection(child_id, to_prune_fsi_set):
                            if log_dict is not None:
                                fsi = ott.get_flag_set_key(child_id)
                                fd = pruned_dict.get(fsi)
                                if fd is None:
                                    pruned_dict[fsi] = {'anc_ott_id_pruned': [child_id]}
                                else:
                                    fd['anc_ott_id_pruned'].append(child_id)
                            num_pruned_anc_nodes += 1
                        else:
                            c.append(child_id)
                    children = c
                    nc = len(children)
                    if nc < 2:
                        if nc == 1:
                            num_monotypic_nodes += 1
                        else:
                            num_tips += 1
                if ott_id not in first_children:
                    out.write(',')
                else:
                    first_children.remove(ott_id)
                if bool(children):
                    out.write('(')
                    first_children.add(children[0])
                    last_children.add(children[-1])
                    stack.append((ott_id,)) # a tuple will signal exiting a node...
                    stack.extend([i for i in reversed(children)])
                    continue
            n = ott.get_label(ott_id, label_style)
            n = quote_newick_name(n)
            out.write(n)
            if ott_id in last_children:
                out.write(')')
                last_children.remove(ott_id)
        out.write(';')
    if create_log_dict:
        log_dict['pruned'] = {}
        for fsi, obj in pruned_dict.items():
            f = pfd[fsi]
            f.sort()
            obj['flags_causing_prune'] = f
            nk = ','.join(f)
            log_dict['pruned'][nk] = obj
        log_dict['num_tips'] = num_tips
        log_dict['num_pruned_anc_nodes'] = num_pruned_anc_nodes
        log_dict['num_nodes'] = num_nodes
        log_dict['num_non_leaf_nodes'] = num_nodes - num_tips
        log_dict['num_non_leaf_nodes_with_multiple_children'] = num_nodes - num_tips - num_monotypic_nodes
        log_dict['num_monotypic_nodes'] = num_monotypic_nodes
    return log_dict
class _TransitionalNode(object):
    def __init__(self, ott_id=None, par=None):
        self.par = par
        #self.ott_id = ott_id
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
    def create_leaf_set(self, leaves):
        if self.children:
            for c in self.children:
                c.create_leaf_set(leaves)
        elif self.ott_id is not None:
            leaves.add(self.ott_id)

_CACHES = {'ottid2parentottid': ('ottID2parentOttId', 'ott ID-> parent\'s ott ID. root maps to -1', ),
           'ottid2preorder': ('ottID2preorder', 'ott ID -> preorder #', ),
           'preorder2ottid': ('preorder2ottID', 'preorder # -> ott ID', ),
           'ottid2uniq': ('ottID2uniq', 'ott ID -> uniqname for those IDs that have a uniqname field', ),
           'uniq2ottid': ('uniq2ottID', 'uniqname -> ott ID for those IDs that have a uniqname', ),
           'name2ottid': ('name2ottID', 'maps a taxon name -> ott ID ', ),
           'homonym2ottid': ('homonym2ottID', 'maps a taxon name -> tuple of OTT IDs ', ),
           'nonhomonym2ottid': ('nonhomonym2ottID', 'maps a taxon name -> single OTT ID ', ),
           'ottid2names': ('ottID2names', 'ottID to a name or list/tuple of names', ),
           'root': ('root', 'name and ott_id of the root of the taxonomy', ),
           'preorder2tuple': ('preorder2tuple', '''preorder # to a node definition
Each node definition is a tuple of preorder numbers:
    leaves will be: (parent, next_sib)
    internals will be: (parent, next_sib, first_child, last_child)
if a node is the last child of its parent, next_sib will be None
also in the map is 'root' -> root preorder number
''', ),
           'ottid2sources': ('ottIDsources', '''maps an ott ID to a dict. The value
holds a mapping of a source taxonomy name to the ID of this ott ID in that
taxonomy.''',),
           'ottid2flags': ('ottID2flags', '''maps an ott ID to an integer that can be looked up in the flag_set_id2flag_set
dictionary. Absence of a ott ID means that there were no flags set.''',),
           'flagsetid2flagset': ('flagSetID2FlagSet',
                                 'maps an integer to set of flags. Used to compress the flags field'),
           'taxonomicsources': ('taxonomicSources', 'the set of all taxonomic source prefixes'),
           'ncbi2ottid': ('ncbi2ottID', 'maps an ncbi to an ott ID or list of ott IDs'),
           'forwardingtable': ('forward_table', 'maps a deprecated ID to its forwarded ID')}
_SECOND_LEVEL_CACHES = set(['ncbi2ottid'])
class CacheNotFoundError(RuntimeError):
    def __init__(self, m):
        RuntimeError.__init__(self, 'Cache {} not found'.format(m))
class OTT(object):
    TREEMACHINE_SUPPRESS_FLAGS = _TREEMACHINE_PRUNE_FLAGS
    def __init__(self, ott_dir=None, **kwargs):
        self._config = kwargs.get('config')
        if self._config is None:
            self._config = get_config_object()
        if ott_dir is None:
            ott_dir = self._config.get_config_setting('ott', 'parent')
        if ott_dir is None:
            raise ValueError('Either the ott_dir arg must be used or "parent" must '\
                             'exist in the "[ott]" section of your config (~/.peyotl/config by default)')
        self.ott_dir = ott_dir
        if not os.path.isdir(self.ott_dir):
            raise ValueError('"{}" is not a directory'.format(self.ott_dir))
        #self.skip_prefixes = ('environmental samples (', 'uncultured (', 'Incertae Sedis (')
        self.skip_prefixes = ('environmental samples (',)
        self._ott_id_to_names = None
        self._ott_id2par_ott_id = None
        self._version = None
        self._root_name = None
        self._root_ott_id = None
        self._name2ott_ids = None
        self._ott_id_to_flags = None
        self._ott_id_to_sources = None
        self._flag_set_id2flag_set = None
        self._taxonomic_sources = None
        self._ncbi_2_ott_id = None
        self._forward_table = None
    def create_ncbi_to_ott(self):
        ncbi2ott = {}
        for ott_id, sources in self.ott_id_to_sources.items():
            ncbi = sources.get('ncbi')
            if ncbi is not None:
                if ncbi in ncbi2ott:
                    prev = ncbi2ott[ncbi]
                    if isinstance(prev, list):
                        prev.append(ott_id)
                    else:
                        ncbi2ott[ncbi] = [prev, ott_id]
                else:
                    ncbi2ott[ncbi] = ott_id
        return ncbi2ott
    def has_flag_set_key_intersection(self, ott_id, taboo):
        flag_set_key = self.ott_id_to_flags.get(ott_id)
        if flag_set_key is None:
            return False
        return flag_set_key in taboo._flag_set_keys
    def get_flag_set_key(self, ott_id):
        return self.ott_id_to_flags.get(ott_id)

    def ncbi(self, ncbi_id):
        if self._ncbi_2_ott_id is None:
            try:
                self._ncbi_2_ott_id = self._load_pickled('ncbi2ottID')
            except CacheNotFoundError:
                d = self.create_ncbi_to_ott()
                self._ncbi_2_ott_id = d
                _write_pickle(self.ott_dir, 'ncbi2ottID', d)

        return self._ncbi_2_ott_id[ncbi_id]
    def convert_flag_string_set_to_union(self, flag_set):
        '''Converts a set of flags to a set integers that represent
        the flag_set keys (in this OTT wrapper) which have any intersection
        with flag_set. Useful if you are pruning out any taxon
        that has any flag in flag_set, because this allows the
        check to be based on the flag_set_key (rather than translating
        each key to its set of strings.'''
        return OTTFlagUnion(self, flag_set)
    def convert_flag_string_set_to_flag_set_keys(self, flag_set):
        if not isinstance(flag_set, set):
            flag_set = set(flag_set)
        iset = set()
        for k, v in self.flag_set_id_to_flag_set.items():
            inters = flag_set.intersection(v)
            if inters:
                iset.add(k)
        return iset
    @property
    def forward_table(self):
        if self._forward_table is None:
            self._forward_table = self._load_pickled('forwardingTable')
        return self._forward_table
    @property
    def flag_set_id_to_flag_set(self):
        if self._flag_set_id2flag_set is None:
            self._flag_set_id2flag_set = self._load_pickled('flagSetID2FlagSet')
        return self._flag_set_id2flag_set
    @property
    def taxonomic_sources(self):
        if self._taxonomic_sources is None:
            self._taxonomic_sources = self._load_pickled('taxonomicSources')
        return self._taxonomic_sources
    @property
    def version(self):
        if self._version is None:
            with codecs.open(os.path.join(self.ott_dir, 'version.txt'), 'r', encoding='utf-8') as fo:
                self._version = fo.read().strip()
        return self._version
    @property
    def taxonomy_filepath(self):
        return os.path.abspath(os.path.join(self.ott_dir, 'taxonomy.tsv'))
    @property
    def synonyms_filepath(self):
        return os.path.abspath(os.path.join(self.ott_dir, 'synonyms.tsv'))
    @property
    def forwarding_filepath(self):
        return os.path.abspath(os.path.join(self.ott_dir, 'forwards.tsv'))
    @property
    def legacy_forwarding_filepath(self):
        return os.path.abspath(os.path.join(self.ott_dir, 'legacy-forwards.tsv'))
    @property
    def ott_id2par_ott_id(self):
        if self._ott_id2par_ott_id is None:
            fp = self.make('ottid2parentottid')
            self._ott_id2par_ott_id = self._load_cache_filepath(fp)
        return self._ott_id2par_ott_id

    def make(self, target):
        tl = target.lower()
        if tl not in _CACHES:
            c = '\n  '.join(_CACHES.keys())
            raise ValueError('target "{t}" not understood. Must be one of: {a}'.format(t=target, a=c))
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
            if tl in _SECOND_LEVEL_CACHES:
                raise CacheNotFoundError(tl)
            _LOG.debug('building "{}"'.format(fp))
            self._create_caches(out_dir=self.ott_dir)
        else:
            _LOG.debug('"{}" up to date.'.format(fp))
        return fp
    def _load_pickled(self, fn):
        if not fn.endswith('.pickle'):
            fn = fn + '.pickle'
        fp = os.path.join(self.ott_dir, fn)
        return self._load_cache_filepath(fp)
    def _load_cache_filepath(self, fp):
        if not os.path.exists(fp):
            fn = os.path.split(fp)[-1]
            if fn.endswith('.pickle'):
                fn = fn[:-len('.pickle')]
            self.make(fn.lower())
        return _load_pickle_fp_raw(fp)
    @property
    def ott_id_to_flags(self):
        if self._ott_id_to_flags is None:
            self._ott_id_to_flags = self._load_pickled('ottID2flags')
        return self._ott_id_to_flags
    @property
    def ott_id_to_sources(self):
        if self._ott_id_to_sources is None:
            self._ott_id_to_sources = self._load_pickled('ottID2sources')
        return self._ott_id_to_sources
    @property
    def ott_id_to_names(self):
        if self._ott_id_to_names is None:
            self._ott_id_to_names = self._load_pickled('ottID2names')
        return self._ott_id_to_names
    def get_label(self, ott_id, name2label):
        n = self.get_name(ott_id)
        if name2label == OTULabelStyleEnum.CURRENT_LABEL_OTT_ID:
            return u'{n}_ott{o:d}'.format(n=n, o=ott_id)
        return n
    def get_name(self, ott_id):
        name_or_name_list = self.ott_id_to_names.get(ott_id)
        if name_or_name_list is None:
            return None
        if is_str_type(name_or_name_list):
            return name_or_name_list
        return name_or_name_list[0]
    def get_ott_ids(self, name):
        if self._name2ott_ids is None:
            self._name2ott_ids = self._load_pickled('name2ottID')
        return self._name2ott_ids.get(name)
    @property
    def root_name(self):
        if self._root_name is None:
            self._load_root_properties()
        return self._root_name
    @property
    def root_ott_id(self):
        if self._root_ott_id is None:
            self._load_root_properties()
        return self._root_ott_id
    def remove_caches(self, out_dir=None):
        if out_dir is None:
            out_dir = self.ott_dir
        for tup in _CACHES.values():
            fp = os.path.join(out_dir, tup[0] + '.pickle')
            if os.path.exists(fp):
                _LOG.info('Removing cache "{f}"'.format(f=fp))
                os.remove(fp)
            else:
                _LOG.debug('Cache "{f}" was absent (no deletion needed).'.format(f=fp))
    def _create_caches(self, out_dir=None):
        try:
            self._create_pickle_files(out_dir=out_dir)
        except:
            raise # TODO, clean up
    def _create_pickle_files(self, out_dir=None): #pylint: disable=R0914,R0915
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
        'ottID2parentOttId'
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
        id2flag = {} # UID to a key in flag_set_id2flag_set
        id2source = {} # UID to {rank: ... silva: ..., ncbi: ... gbif:..., irmng : , f}
                     # where the value for f is
        flag_set_id2flag_set = {}
        flag_set2flag_set_id = {}
        sources = set()
        flag_set = set()
        f_set_id = 0
        source = {}
        root_ott_id = None
        with codecs.open(taxonomy_file, 'r', encoding='utf-8') as tax_fo:
            it = iter(tax_fo)
            first_line = next(it)
            assert first_line == 'uid\t|\tparent_uid\t|\tname\t|\trank\t|\tsourceinfo\t|\tuniqname\t|\tflags\t|\t\n'
            life_line = next(it)
            root_split = life_line.split('\t|\t')
            uid = int(root_split[0])
            root_ott_id = uid
            assert root_split[1] == ''
            name = root_split[2]
            sourceinfo, uniqname, flags = root_split[4:7]
            self._root_name = name
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
                    source[src] = sid
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
                    flag_set2flag_set_id[f_set] = fsi
                id2flag[uid] = fsi
            if source:
                id2source[uid] = source
                source = {}
            for rown in it:
                ls = rown.split('\t|\t')
                uid, par, name = ls[:3]
                sourceinfo, uniqname, flags = ls[4:7]
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
                if par not in id2par:
                    raise ValueError('parent {} not found in OTT parsing'.format(par))
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
                        source[src] = sid
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
                        flag_set2flag_set_id[f_set] = fsi
                    id2flag[uid] = fsi
                if source:
                    id2source[uid] = source
                    source = {}

                num_lines += 1
                if num_lines % 100000 == 0:
                    _LOG.debug('read {n:d} lines...'.format(n=num_lines))
        _LOG.debug('read taxonomy file. total of {n:d} lines.'.format(n=num_lines))
        _write_pickle(out_dir, 'ottID2parentOttId', id2par)
        synonyms_file = self.synonyms_filepath
        _LOG.debug('Reading "{f}"...'.format(f=synonyms_file))
        if not os.path.isfile(synonyms_file):
            raise ValueError('Expecting to find "{}" based on ott_dir of "{}"'.format(synonyms_file, self.ott_dir))
        num_lines = 0
        with codecs.open(synonyms_file, 'r', encoding='utf-8') as syn_fo:
            it = iter(syn_fo)
            first_line = next(it)
            # modified to allow for final 'source column'
            assert first_line.startswith('name\t|\tuid\t|\ttype\t|\tuniqname')
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
        homonym2id = {}
        nonhomonym2id = {}
        for name, ott_ids in name2id.iteritems():
            if isinstance(ott_ids, tuple) and len(ott_ids) > 1:
                homonym2id[name] = ott_ids
            else:
                nonhomonym2id[name] = ott_ids
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
        self._root_ott_id = root_ott_id
        self._write_root_properties(out_dir, self._root_name, self._root_ott_id)
        _write_pickle(out_dir, 'ottID2preorder', ott_id2preorder)
        _write_pickle(out_dir, 'preorder2ottID', preorder2ott_id)
        _write_pickle(out_dir, 'ottID2uniq', id2uniq)
        _write_pickle(out_dir, 'uniq2ottID', uniq2id)
        _write_pickle(out_dir, 'name2ottID', name2id)
        _write_pickle(out_dir, 'homonym2ottID', homonym2id)
        _write_pickle(out_dir, 'nonhomonym2ottID', nonhomonym2id)
        _write_pickle(out_dir, 'ottID2names', id2name)
        _write_pickle(out_dir, 'ottID2sources', id2source)
        _write_pickle(out_dir, 'ottID2flags', id2flag)
        _write_pickle(out_dir, 'flagSetID2FlagSet', flag_set_id2flag_set)
        _write_pickle(out_dir, 'taxonomicSources', sources)
        forward_table = self._parse_forwarding_files()
        _write_pickle(out_dir, 'forwardingTable', forward_table)
        _LOG.debug('creating tree representation with preorder # to tuples')
        preorder2tuples = {}
        root.par = _TransitionalNode() # fake parent of root
        root.par.preorder_number = None
        root.fill_preorder2tuples(None, preorder2tuples)
        preorder2tuples['root'] = root.preorder_number
        _write_pickle(out_dir, 'preorder2tuple', preorder2tuples)
    def _parse_forwarding_files(self):
        r = {}
        fp_list = [self.forwarding_filepath, self.legacy_forwarding_filepath]
        for fp in fp_list:
            if os.path.exists(fp):
                with codecs.open(fp, 'r', encoding='utf-8') as syn_fo:
                    for line in syn_fo:
                        ls = line.split('\t')
                        try:
                            if ls[0] == 'id': # deal with header
                                continue
                            old_id, new_id = ls[0], ls[1]
                        except:
                            if line.strip():
                                raise RuntimeError('error parsing line in "{}":\n{}'.format(fp, line))
                        if old_id in r:
                            _LOG.warn('fp: "{}" {} -> {} but {} -> {} already.'.format(fp, old_id, new_id, old_id, r[old_id]))
                            assert old_id not in r
                        r[old_id] = new_id
        while True:
            reforward = [(k, v) for k, v in r.items() if v in r]
            if not reforward:
                break
            for oldest_id, old_id in reforward:
                new_id = r[old_id]
                _LOG.debug('Reforwarding {} from {} to {}'.format(oldest_id, old_id, new_id))
                r[oldest_id] = new_id
        return r

    def _write_root_properties(self, out_dir, name, ott_id):
        root_info = {'name': name,
                     'ott_id': ott_id, }
        _write_pickle(out_dir, 'root', root_info)
    def _load_root_properties(self):
        r = self._load_pickled('root')
        self._root_name = r['name']
        self._root_ott_id = r['ott_id']

    def write_newick(self,
                     out,
                     root_ott_id=None,
                     label_style=OTULabelStyleEnum.OTT_ID,
                     prune_flags=None,
                     create_log_dict=False):
        '''
        '''
        if isinstance(label_style, int):
            label_style = OTULabelStyleEnum(label_style)
        if root_ott_id is None:
            root_ott_id = self.root_ott_id
        if label_style not in [OTULabelStyleEnum.OTT_ID, OTULabelStyleEnum.CURRENT_LABEL_OTT_ID]:
            raise NotImplementedError('newick from ott with labels other than ott id')
        o2p = self.ott_id2par_ott_id
        ott2children = make_ott_to_children(o2p)
        return write_newick_ott(out,
                                self,
                                ott2children,
                                root_ott_id,
                                label_style,
                                prune_flags,
                                create_log_dict=create_log_dict)
    def get_anc_lineage(self, ott_id):
        return create_anc_lineage_from_id2par(self.ott_id2par_ott_id, ott_id)

    def _debug_anc_spikes(self, ott_id_list):
        al = [self.get_anc_lineage(o) for o in ott_id_list]
        asl = []
        for a in al:
            asl.append(' -> '.join(['{:<8}'.format(i) for i in a]))
        l = [len(i) for i in asl]
        m = max(l)
        fmt = "{:<8} : {:>%d}" % m
        for n, o in enumerate(ott_id_list):
            _LOG.debug(fmt.format(o, asl[n]))
    def induced_tree(self, ott_id_list, create_monotypic_nodes=False):
        #self._debug_anc_spikes(ott_id_list)
        return create_tree_from_id2par(self.ott_id2par_ott_id, ott_id_list, create_monotypic_nodes=create_monotypic_nodes)

    def check_if_above_root(self, curr_id, known_below_root, known_above_root, root_ott_id):
        if (root_ott_id is None):
            return False
        if curr_id in known_below_root:
            return False
        if curr_id in known_above_root:
            return True
        oi2poi = self.ott_id2par_ott_id
        new_id_list = []
        assert curr_id is not None
        while True:
            new_id_list.append(curr_id)
            if (curr_id is None) or (curr_id in known_above_root):
                known_above_root.update(new_id_list)
                return True
            curr_id = oi2poi.get(curr_id)
            if (curr_id in known_below_root) or (curr_id == root_ott_id):
                known_below_root.update(new_id_list)
                return False

    def check_if_in_pruned_subtree(self, curr_id, known_unpruned, known_pruned, to_prune_fsi_set):
        if curr_id in known_pruned:
            return True
        if curr_id in known_unpruned:
            return False
        oi2poi = self.ott_id2par_ott_id
        new_id_list = []
        assert curr_id is not None
        while True:
            new_id_list.append(curr_id)
            if (self.has_flag_set_key_intersection(curr_id, to_prune_fsi_set)) or (curr_id in known_pruned):
                known_pruned.update(new_id_list)
                return True
            curr_id = oi2poi.get(curr_id)
            if (curr_id is None) or (curr_id in known_unpruned):
                known_unpruned.update(new_id_list)
                return False

    def map_ott_ids(self, ott_id_list, to_prune_fsi_set, root_ott_id):
        '''returns:
          - a list of recognized ott_ids.
          - a list of unrecognized ott_ids
          - a list of ott_ids that forward to unrecognized ott_ids
          - a list of ott_ids that do not appear in the tree because they are flagged to be pruned.
          - a list of ott_ids that do not appear in the tree because they are above the root of the relevant subtree.
          - a dict mapping input Id to forwarded Id
        The relative order will be the input order, but the unrecognized elements will
            be deleted.
        '''
        mapped, unrecog, forward2unrecog, pruned, above_root, old2new = [], [], [], [], [], {}
        known_unpruned, known_pruned = set(), set()
        known_above_root, known_below_root = set(), set()
        oi2poi = self.ott_id2par_ott_id
        ft = self.forward_table
        for old_id in ott_id_list:
            if old_id in oi2poi:
                if self.check_if_above_root(old_id, known_above_root, known_below_root, root_ott_id):
                    above_root.append(old_id)
                elif (to_prune_fsi_set is not None) and \
                    self.check_if_in_pruned_subtree(old_id, known_unpruned, known_pruned, to_prune_fsi_set):
                    pruned.append(old_id)
                else:
                    mapped.append(old_id)
            else:
                new_id = ft.get(old_id)
                if new_id is None:
                    unrecog.append(old_id)
                else:
                    if new_id in oi2poi:
                        if (to_prune_fsi_set is not None) and \
                            self.check_if_in_pruned_subtree(new_id, known_unpruned, known_pruned, to_prune_fsi_set):
                            pruned.append(old_id) # could be in a forward2pruned
                        else:
                            old2new[old_id] = new_id
                            mapped.append(new_id)
                    else:
                        forward2unrecog.append(old_id)
        return mapped, unrecog, forward2unrecog, pruned, above_root, old2new

if _PICKLE_AS_JSON:
    def _write_pickle(directory, fn, obj):
        fp = os.path.join(directory, fn + '.pickle')
        _LOG.debug('Creating "{p}"'.format(p=fp))
        with open(fp, 'wb') as fo:
            write_as_json(obj, fo)

    def _load_pickle_fp_raw(fp):
        return read_as_json(fp)
else:
    def _write_pickle(directory, fn, obj):
        fp = os.path.join(directory, fn + '.pickle')
        _LOG.debug('Creating "{p}"'.format(p=fp))
        with open(fp, 'wb') as fo:
            pickle.dump(obj, fo)

    def _load_pickle_fp_raw(fp):
        return pickle.load(open(fp, 'rb'))

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
            root = _TransitionalNode(ott_id=gp_id)
            ott2transitional[gp_id] = root
            return root
    par = _TransitionalNode(ott_id=par_ott_id, par=gp)
    ott2transitional[par_ott_id] = par
    return par

def make_tree_from_taxonomy(id2par):
    ott2transitional = {}
    for ott_id, par_ott_id in id2par.items():
        par = _generate_parent(id2par, par_ott_id, ott2transitional)
        nd = _TransitionalNode(ott_id=ott_id, par=par)
        ott2transitional[ott_id] = nd
    return ott2transitional

def make_ott_to_children(id2par):
    ott2children = {}
    emptyTuple = tuple()
    for ott_id, par_ott_id in id2par.items():
        pc = ott2children.get(par_ott_id)
        if (pc is None) or (pc is emptyTuple):
            ott2children[par_ott_id] = [ott_id]
        else:
            pc.append(ott_id)
        if ott_id not in ott2children:
            ott2children[ott_id] = emptyTuple
    return ott2children

class TaxonomyDes2AncLineage(object):
    def __init__(self, des_to_anc_list):
        self._des_to_anc_list = des_to_anc_list
        assert bool(des_to_anc_list)
    def __str__(self):
        return '{r} at {i}'.format(r=self.__repr__(), i=hex(id(self)))
    def __repr__(self):
        return 'TaxonomyDes2AncLineage({l})'.format(l=repr(self._des_to_anc_list))

def create_pruned_and_taxonomy_for_tip_ott_ids(tree_proxy, ott, create_monotypic_nodes=False):
    '''returns a pair of trees:
        the first is that is a pruned version of tree_proxy created by pruning
            any leaf that has no ott_id and every internal that does not have
            any descendant with an ott_id. Nodes of out-degree 1 are suppressed
            as part of the TreeWithPathsInEdges-style.
        the second is the OTT induced tree for these ott_ids
    '''
    # create and id2par that has ott IDs only at the tips (we are
    #   ignoring mappings at internal nodes.
    # OTT IDs are integers, and the nodeIDs are strings - so we should not get clashes.
    #TODO consider prefix scheme
    ott_ids = []
    ottId2OtuPar = {}
    for node in tree_proxy:
        if node.is_leaf:
            ott_id = node.ott_id
            if ott_id is not None:
                ott_ids.append(ott_id)
                assert isinstance(ott_id, int)
                parent_id = node.parent._id
                ottId2OtuPar[ott_id] = parent_id
        else:
            assert is_str_type(node._id)
            edge = node.edge
            if edge is not None:
                parent_id = node.parent._id
                ottId2OtuPar[node._id] = parent_id
            else:
                ottId2OtuPar[node._id] = None
    pruned_phylo = create_tree_from_id2par(ottId2OtuPar, ott_ids, create_monotypic_nodes=create_monotypic_nodes)
    taxo_tree = ott.induced_tree(ott_ids)
    return pruned_phylo, taxo_tree



if __name__ == '__main__':
    import sys
    cout = codecs.getwriter('utf-8')(sys.stdout)
    o = OTT()
    #print('taxonomic sources = "{}"'.format('", "'.join([iii for iii in o.taxonomic_sources])))
    #print(o.ncbi(1115784))
    o.write_newick(cout, label_style=OTULabelStyleEnum.CURRENT_LABEL_OTT_ID, prune_flags=_TREEMACHINE_PRUNE_FLAGS)
    cout.write('\n')
    '''fstrs = ['{k:d}: {v}'.format(k=k, v=v) for k, v in o.flag_set_id_to_flag_set.items()]
    print('flag_set_id_to_flag_set =\n  {}'.format('\n  '.join(fstrs)))
    for ott_id, info in o.ott_id_to_sources.items():
        if 'ncbi' in info:
            print('OTT {o:d} => NCBI {n:d}'.format(o=ott_id, n=info['ncbi']))
    print(len(o.ott_id2par_ott_id), 'ott IDs')
    print('call')
    print(o.get_anc_lineage(593937)) # This is the OTT id of a species in the Asterales system
    print(o.root_name)
    o.induced_tree([458721, 883864, 128315])
    '''
