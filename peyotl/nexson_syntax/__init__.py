 #!/usr/bin/env python
'''Functions for converting between the different representations
of NexSON and the NeXML representation.
See https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/NexSON

Most notable functions are:
    write_obj_as_nexml,
    get_ot_study_info_from_nexml,

'''
from peyotl.nexson_syntax.helper import ConversionConfig, \
                                        NexsonConverter, \
                                        detect_nexson_version, \
                                        get_nexml_el, \
                                        _add_value_to_dict_bf, \
                                        _get_index_list_of_values, \
                                        _index_list_of_values, \
                                        _is_badgerfish_version, \
                                        _is_by_id_hbf, \
                                        _is_direct_hbf, \
                                        _is_supported_nexson_vers, \
                                        BADGER_FISH_NEXSON_VERSION, \
                                        DEFAULT_NEXSON_VERSION, \
                                        DIRECT_HONEY_BADGERFISH, \
                                        NEXML_NEXSON_VERSION, \
                                        BY_ID_HONEY_BADGERFISH, \
                                        SUPPORTED_NEXSON_VERSIONS
from peyotl.utility.input_output import read_as_json, write_as_json
from peyotl.utility.str_util import flush_utf_8_writer, \
                                    UNICODE, \
                                    is_str_type, \
                                    get_utf_8_string_io_writer
from peyotl.nexson_syntax.optimal2direct_nexson import Optimal2DirectNexson
from peyotl.nexson_syntax.direct2optimal_nexson import Direct2OptimalNexson
from peyotl.nexson_syntax.badgerfish2direct_nexson import Badgerfish2DirectNexson
from peyotl.nexson_syntax.direct2badgerfish_nexson import Direct2BadgerfishNexson
from peyotl.nexson_syntax.nexson2nexml import Nexson2Nexml
from peyotl.nexson_syntax.nexml2nexson import Nexml2Nexson
from peyotl.nexson_syntax.inspect import count_num_trees
from peyotl.utility import get_logger
import xml.dom.minidom
import codecs
import re

_CONVERTIBLE_FORMATS = frozenset([NEXML_NEXSON_VERSION,
                                  DIRECT_HONEY_BADGERFISH,
                                  BADGER_FISH_NEXSON_VERSION,
                                  BY_ID_HONEY_BADGERFISH,
                                  '0.0',
                                  '1.0',
                                  '1.2', ])
_LOG = get_logger(__name__)

def iter_otu(nexson, nexson_version=None):
    if nexson_version is None:
        nexson_version = detect_nexson_version(nexson)
    if not _is_by_id_hbf(nexson_version):
        raise NotImplementedError('iter_otu is only supported for nexson 1.2 at this point')
    nexml = get_nexml_el(nexson)
    for og in nexml.get('otusById', {}).values():
        for otu_id, otu in og.get('otuById', {}).items():
            yield otu_id, otu

def strip_to_meta_only(blob, nexson_version):
    if nexson_version is None:
        nexson_version = detect_nexson_version(blob)
    nex = get_nexml_el(blob)
    if _is_by_id_hbf(nexson_version):
        for otus_group in nex.get('otusById', {}).values():
            if 'otuById' in otus_group:
                del otus_group['otuById']
        for trees_group in nex.get('treesById', {}).values():
            tree_group = trees_group['treeById']
            key_list = tree_group.keys()
            for k in key_list:
                tree_group[k] = None
    else:
        otus = nex['otus']
        if not isinstance(otus, list):
            otus = [otus]
        for otus_group in otus:
            if 'otu' in otus_group:
                del otus_group['otu']
        trees = nex['trees']
        if not isinstance(trees, list):
            trees = [trees]
        for trees_group in trees:
            tree_list = trees_group.get('tree')
            if not isinstance(tree_list, list):
                tree_list = [tree_list]
            t = [{'id': i.get('@id')} for i in tree_list]
            trees_group['tree'] = t

def _otu_dict_to_otumap(otu_dict):
    d = {}
    for v in otu_dict.values():
        k = v['^ot:originalLabel']
        mv = d.get(k)
        if mv is None:
            mv = {}
            d[k] = mv
        elif isinstance(mv, list):
            mv.append({})
            mv = mv[-1]
        else:
            mv = [mv, {}]
            mv = mv[-1]
            d[k] = mv
        for mk in ['^ot:ottId', '^ot:ottTaxonName']:
            mvv = v.get(mk)
            if mvv is not None:
                mv[mk] = mvv
    return d

def _get_content_id_from(content, **kwargs):
    if content in PhyloSchema._no_content_id_types:  #pylint: disable=W0212
        return None
    elif content == 'tree':
        return kwargs.get('tree_id')
    elif content == 'subtree':
        subtree_id = kwargs.get('subtree_id')
        if subtree_id is None:
            subtree_id = kwargs.get('node_id')
        return (kwargs.get('tree_id'), subtree_id)
    elif content == 'otus':
        return kwargs.get('otus_id')
    elif content == 'otu':
        return kwargs.get('otu_id')
    elif content == ('otus', 'otumap'):
        return kwargs.get('otus_id')

def _sniff_content_from_kwargs(**kwargs):
    c_id = kwargs.get('tree_id')
    if c_id is not None:
        s_id = kwargs.get('subtree_id')
        if s_id is None:
            s_id = kwargs.get('node_id')
        if s_id is None:
            return 'tree', c_id
        return 'subtree', (c_id, s_id)
    c_id = kwargs.get('otus_id')
    if c_id is not None:
        return 'otus', c_id
    c_id = kwargs.get('otu_id')
    if c_id is not None:
        return 'otu', c_id
    return 'study', None

def get_git_sha(blob):
    return blob['sha']

def create_content_spec(**kwargs):
    '''Sugar. factory for a PhyloSchema object.

    Repackages the kwargs to kwargs for PhyloSchema so that our
    PhyloSchema.__init__ does not have to be soo rich
    '''
    format_str = kwargs.get('format', 'nexson')
    nexson_version = kwargs.get('nexson_version', 'native')
    otu_label = kwargs.get('otu_label')
    if otu_label is None:
        otu_label = kwargs.get('tip_label')
    content = kwargs.get('content')
    if content is not None:
        content_id = kwargs.get('content_id')
        if content_id is None:
            content_id = _get_content_id_from(**kwargs)
    else:
        content, content_id = _sniff_content_from_kwargs(**kwargs)
    if content is None:
        content = 'study'
    return PhyloSchema(content=content,
                       content_id=content_id,
                       format_str=format_str,
                       version=nexson_version,
                       otu_label=otu_label,
                       repo_nexml2json=kwargs.get('repo_nexml2json'),
                       bracket_ingroup=bool(kwargs.get('bracket_ingroup', False)),
                       cull_nonmatching=kwargs.get('cull_nonmatching'))

class PhyloSchema(object):
    '''Simple container for holding the set of variables needed to
    convert from one format to another (with error checking).

    The primary motivation for this class is to:
        1. generate type conversion errors up front when some one requests
            a particular coercion. For example, this allows the phylesystem
            api to raise an error before it fetches the data in cases in which
            the user is requesting a format/content combination is not
            currently supported (or not possible)
        2. allow that agreed-upon coercion to be done later with a simple
            call to convert or serialize. So the class acts like a closure
            that can transform any nexson to the desired format (if NexSON
            has the necessary content)
    `bracket_ingroup` is currently only used in newick string export. If True, then
        [pre-ingroup-marker] and [post-ingroup-marker] comments will surround the ingroup
        definition in the tree.
    '''
    _format_list = ('newick', 'nexson', 'nexml', 'nexus')
    NEWICK, NEXSON, NEXML, NEXUS = range(4)
    _extension2format = {
        '.nexson' : 'nexson',
        '.nexml': 'nexml',
        '.nex': 'nexus',
        '.tre': 'newick',
        '.nwk': 'newick',
    }
    _otu_label2prop = {'ot:originallabel': '^ot:originalLabel',
                       'ot:ottid': '^ot:ottId',
                       'ot:otttaxonname': '^ot:ottTaxonName', }
    _otu_label_list = _otu_label2prop.keys()
    _NEWICK_PROP_VALS = _otu_label2prop.values()
    _no_content_id_types = set(['study', 'meta', 'treelist'])
    _tup_content_id_types = set(['subtree'])
    _str_content_id_types = set(['tree', 'otus', 'otu', 'otumap', 'file'])
    _content_types = set(['file', 'study', 'tree', 'meta', 'otus', 'otu', 'otumap', 'subtree', 'treelist'])
    def __init__(self, schema=None, **kwargs):
        '''Checks:
            'schema',
            'type_ext', then
            'output_nexml2json' (implicitly NexSON)
            If exporting to a non-nexson format, `otu_label` (and then
                `tip_label`are checked) to determine how to label the tips
                'ot:originallabel', 'ot:ottid', and 'ot:otttaxonname'
                are supported values
        '''
        self.content = kwargs.get('content', 'study')
        self.bracket_ingroup = bool(kwargs.get('bracket_ingroup', False))
        self.content_id = kwargs.get('content_id')
        self.cull_nonmatching = kwargs.get('cull_nonmatching')
        err_msg = 'expected cull_nonmatching to be "true" or "false" or the boolean versions of those values. found {}'
        #pylint: disable=E1103
        if is_str_type(self.cull_nonmatching):
            if self.cull_nonmatching.lower() in ['true', '1']:
                self.cull_nonmatching = True
            else:
                if self.cull_nonmatching.lower() not in ['false', '0']:
                    raise ValueError(err_msg.format(kwargs.get('cull_nonmatching')))
                self.cull_nonmatching = False
        elif self.cull_nonmatching is not None and not isinstance(self.cull_nonmatching, bool):
            raise ValueError(err_msg.format('a non-boolean and non-string value'))

        if self.content not in PhyloSchema._content_types:
            raise ValueError('"content" must be one of: "{}"'.format('", "'.join(PhyloSchema._content_types)))
        if self.content in PhyloSchema._no_content_id_types:
            if self.content_id is not None:
                raise ValueError('No content_id expected for "{}" content'.format(self.content))
        elif self.content in PhyloSchema._str_content_id_types:
            if not (self.content_id is None or is_str_type(self.content_id)):
                raise ValueError('content_id for "{}" content must be a string (if provided)'.format(self.content))
        else:
            is_list = isinstance(self.content_id, list) or isinstance(self.content_id, tuple)
            if (self.content_id is None) or (not is_list) or len(self.content_id) != 2:
                raise ValueError('Expecting 2 content_ids for the "subtree" content')
        if schema is not None:
            #_LOG.debug('schema from schema arg')
            self.format_str = schema.lower()
        elif kwargs.get('type_ext') is not None:
            #_LOG.debug('schema from type_ext arg')
            ext = kwargs['type_ext'].lower()
            try:
                self.format_str = PhyloSchema._extension2format[ext]
            except:
                raise ValueError('file extension "{}" not recognized'.format(kwargs['type_ext']))
        elif kwargs.get('output_nexml2json') is not None:
            #_LOG.debug('schema from output_nexml2json arg')
            self.format_str = 'nexson'
            self.version = kwargs['output_nexml2json']
        else:
            #_LOG.debug('schema from format_str arg')
            self.format_str = kwargs.get('format_str')
        if self.format_str is None:
            raise ValueError('Expecting "format_str", "schema", or "type_ext" argument')
        try:
            #_LOG.debug('self.format_str = {}'.format(self.format_str))
            self.format_code = PhyloSchema._format_list.index(self.format_str)
            #_LOG.debug('self.format_code = {}'.format(str(self.format_code)))
        except:
            raise ValueError('format "{}" not recognized'.format(self.format_str))
        if self.format_code == PhyloSchema.NEXSON:
            try:
                if not hasattr(self, 'version'):
                    if 'output_nexml2json' in kwargs:
                        self.version = kwargs['output_nexml2json']
                    else:
                        self.version = kwargs['version']
                if self.version == 'native':
                    self.version = kwargs['repo_nexml2json']
                if not _is_supported_nexson_vers(self.version):
                    raise ValueError('The "{}" version of NexSON is not supported'.format(self.version))
            except:
                msg = 'Expecting version of NexSON to be specified using ' \
                      '"output_nexml2json" argument (or via some other mechanism)'
                raise ValueError(msg)
        else:
            if self.content in ['meta']:
                raise ValueError('The "{}" content can only be returned in NexSON'.format(self.content))
            if kwargs.get('otu_label') is not None:
                self.otu_label = kwargs['otu_label'].lower()
            else:
                self.otu_label = kwargs.get('tip_label', 'ot:originallabel').lower()
            if self.otu_label not in PhyloSchema._otu_label_list:
                with_ns = 'ot:{}'.format(self.otu_label)
                if with_ns in PhyloSchema._otu_label_list:
                    self.otu_label = with_ns
                else:
                    m = '"otu_label" or "tip_label" must be one of "{}"'
                    m = m.format('", "'.join(PhyloSchema._otu_label_list))
                    raise ValueError(m)
            self.otu_label_prop = PhyloSchema._otu_label2prop[self.otu_label]
    @property
    def description(self):
        if self.format_code == PhyloSchema.NEXSON:
            return 'NexSON v{v}'.format(v=self.version)
        elif self.format_code == PhyloSchema.NEXML:
            return 'NeXML'
        elif self.format_code == PhyloSchema.NEXUS:
            return 'NEXUS'
        elif self.format_code == PhyloSchema.NEWICK:
            return 'Newick'
    def can_convert_from(self, src_schema=None): #pylint: disable=W0613
        if self.format_code == PhyloSchema.NEXSON:
            return self.content != 'subtree'
        if self.content == 'study':
            return True
        if self.content in set(['tree', 'subtree']):
            return self.format_code in [PhyloSchema.NEWICK, PhyloSchema.NEXUS]
        return False
    def is_json(self):
        return self.format_code == PhyloSchema.NEXSON
    def is_xml(self):
        return self.format_code == PhyloSchema.NEXML
    def is_text(self):
        return self.format_code in (PhyloSchema.NEXUS, PhyloSchema.NEWICK)
    def _phylesystem_api_params(self):
        d = {}
        if self.format_code == PhyloSchema.NEXSON:
            d['output_nexml2json'] = self.version
        else:
            if self.otu_label != 'ot:originallabel':
                d['otu_label'] = self.otu_label
        if self.content == 'tree':
            if self.cull_nonmatching:
                d['cull_nonmatching'] = 'true'
        return d
    def _phylesystem_api_ext(self):
        if self.format_code == PhyloSchema.NEXSON:
            return ''
        elif self.format_code == PhyloSchema.NEWICK:
            return '.tre'
        elif self.format_code == PhyloSchema.NEXUS:
            return '.nex'
        elif self.format_code == PhyloSchema.NEXML:
            return '.nexml'
        else:
            assert False
    def phylesystem_api_url(self, base_url, study_id):
        '''Returns URL and param dict for a GET call to phylesystem_api
        '''
        p = self._phylesystem_api_params()
        e = self._phylesystem_api_ext()
        if self.content == 'study':
            return '{d}/study/{i}{e}'.format(d=base_url, i=study_id, e=e), p
        elif self.content == 'tree':
            if self.content_id is None:
                return '{d}/study/{i}/tree{e}'.format(d=base_url, i=study_id, e=e), p
            return '{d}/study/{i}/tree/{t}{e}'.format(d=base_url, i=study_id, t=self.content_id, e=e), p
        elif self.content == 'subtree':
            assert self.content_id is not None
            t, n = self.content_id
            p['subtree_id'] = n
            return '{d}/study/{i}/subtree/{t}{e}'.format(d=base_url, i=study_id, t=t, e=e), p
        elif self.content == 'meta':
            return '{d}/study/{i}/meta{e}'.format(d=base_url, i=study_id, e=e), p
        elif self.content == 'otus':
            if self.content_id is None:
                return '{d}/study/{i}/otus{e}'.format(d=base_url, i=study_id, e=e), p
            return '{d}/study/{i}/otus/{t}{e}'.format(d=base_url, i=study_id, t=self.content_id, e=e), p
        elif self.content == 'otu':
            if self.content_id is None:
                return '{d}/study/{i}/otu{e}'.format(d=base_url, i=study_id, e=e), p
            return '{d}/study/{i}/otu/{t}{e}'.format(d=base_url, i=study_id, t=self.content_id, e=e), p
        elif self.content == 'otumap':
            return '{d}/otumap/{i}{e}'.format(d=base_url, i=study_id, e=e), p
        else:
            assert False

    def serialize(self, src, output_dest=None, src_schema=None):
        return self.convert(src, serialize=True, output_dest=output_dest, src_schema=src_schema)
    def convert(self, src, serialize=None, output_dest=None, src_schema=None):
        if src_schema is None:
            src_format = PhyloSchema.NEXSON
            current_format = None
        else:
            src_format = src_schema.format_code
            current_format = src_schema.version
        if not self.can_convert_from():
            m = 'Conversion of {c} to {d} is not supported'.format(c=self.content, d=self.description)
            raise NotImplementedError(m)
        if src_format != PhyloSchema.NEXSON:
            raise NotImplementedError('Only conversion from NexSON is currently supported')
        if self.format_code == PhyloSchema.NEXSON:
            d = src
            if self.content == 'study':
                d = convert_nexson_format(src,
                                          out_nexson_format=self.version,
                                          current_format=current_format,
                                          remove_old_structs=True,
                                          pristine_if_invalid=False,
                                          sort_arbitrary=False)
            elif self.content in ('tree', 'subtree'):
                if self.content == 'tree' and self.cull_nonmatching:
                    d = cull_nonmatching_trees(d, self.content_id, current_format)
                    d = convert_nexson_format(d,
                                              out_nexson_format=self.version,
                                              current_format=current_format,
                                              remove_old_structs=True,
                                              pristine_if_invalid=False,
                                              sort_arbitrary=False)

                else:
                    i_t_o_list = extract_tree_nexson(d, self.content_id, current_format)
                    d = {}
                    for ito_tup in i_t_o_list:
                        i, t = ito_tup[0], ito_tup[1]
                        d[i] = t
            elif self.content == 'meta':
                strip_to_meta_only(d, current_format)
            elif self.content == 'otus':
                d = extract_otus_nexson(d, self.content_id, current_format)
            elif self.content == 'otu':
                d = extract_otu_nexson(d, self.content_id, current_format)
            elif self.content == 'otumap':
                if self.content_id is None:
                    r = extract_otu_nexson(d, None, current_format)
                else:
                    p = extract_otus_nexson(d, self.content_id, current_format)
                    if p is None:
                        r = extract_otu_nexson(d, self.content_id, current_format)
                    else:
                        r = {}
                        for v in p.values():
                            r.update(v.get('otuById', {}))
                if not r:
                    return None
                d = _otu_dict_to_otumap(r)
            elif self.content == 'treelist':
                i_t_o_list = extract_tree_nexson(d,
                                                 self.content_id,
                                                 current_format)
                d = [i[0] for i in i_t_o_list]
            if d is None:
                return None
            if serialize:
                if output_dest:
                    write_as_json(d, output_dest)
                    return None
                else:
                    f, wrapper = get_utf_8_string_io_writer()
                    write_as_json(d, wrapper)
                    flush_utf_8_writer(wrapper)
                    return f.getvalue()
            else:
                return d
        # Non-NexSON types go here...
        if (serialize is not None) and (not serialize):
            raise ValueError('Conversion without serialization is only supported for the NexSON format')
        if output_dest:
            if is_str_type(output_dest):
                output_dest = codecs.open(output_dest, 'w', encoding='utf-8')
        if self.format_code == PhyloSchema.NEXML:
            if output_dest:
                write_obj_as_nexml(src, output_dest, addindent=' ', newl='\n', otu_label=self.otu_label_prop)
                return
            return convert_to_nexml(src, addindent=' ', newl='\n', otu_label=self.otu_label_prop)
        elif self.format_code in [PhyloSchema.NEXUS, PhyloSchema.NEWICK]:
            if self.content in ('tree', 'subtree'):
                if isinstance(self.content_id, list) or isinstance(self.content_id, tuple):
                    ci, subtree_id = self.content_id
                else:
                    ci, subtree_id = self.content_id, None
            else:
                ci, subtree_id = None, None
            response = extract_tree(src, ci, self, subtree_id=subtree_id)
            # these formats are always serialized...
            if output_dest:
                output_dest.write(response)
                output_dest.write('\n')
            return response
        assert False



def get_ot_study_info_from_nexml(src=None,
                                 nexml_content=None,
                                 encoding=u'utf8',
                                 nexson_syntax_version=DEFAULT_NEXSON_VERSION):
    '''Converts an XML doc to JSON using the honeybadgerfish convention (see to_honeybadgerfish_dict)
    and then prunes elements not used by open tree of life study curartion.

    If nexml_content is provided, it is interpreted as the contents
    of an NeXML file in utf-8 encoding.

    If nexml_content is None, then the src arg will be used src can be either:
        * a file_object, or
        * a string
    If `src` is a string then it will be treated as a filepath unless it
        begins with http:// or https:// (in which case it will be downloaded
        using peyotl.utility.download)
    Returns a dictionary with the keys/values encoded according to the honeybadgerfish convention
    See https://github.com/OpenTreeOfLife/api.opentreeoflife.org/wiki/HoneyBadgerFish

    Currently:
        removes nexml/characters @TODO: should replace it with a URI for
            where the removed character data can be found.
    '''
    if _is_by_id_hbf(nexson_syntax_version):
        nsv = DIRECT_HONEY_BADGERFISH
    else:
        nsv = nexson_syntax_version
    if nexml_content is None:
        if is_str_type(src):
            if src.startswith('http://') or src.startswith('https://'):
                from peyotl.utility import download
                nexml_content = download(url=src, encoding=encoding)
            else:
                with codecs.open(src, 'r', encoding=encoding) as src:
                    nexml_content = src.read().encode('utf-8')
        else:
            nexml_content = src.read().encode('utf-8')
    doc = xml.dom.minidom.parseString(nexml_content)
    doc_root = doc.documentElement

    ccfg = ConversionConfig(output_format=nsv, input_format=NEXML_NEXSON_VERSION)
    converter = Nexml2Nexson(ccfg)
    o = converter.convert(doc_root)
    if _is_by_id_hbf(nexson_syntax_version):
        o = convert_nexson_format(o, BY_ID_HONEY_BADGERFISH, current_format=nsv)
    if 'nex:nexml' in o:
        n = o['nex:nexml']
        del o['nex:nexml']
        o['nexml'] = n
    return o

def _nexson_directly_translatable_to_nexml(vers):
    'TEMP: until we refactor nexml writing code to be more general...'
    return (_is_badgerfish_version(vers)
            or _is_direct_hbf(vers)
            or vers == 'nexml')

def write_obj_as_nexml(obj_dict,
                       file_obj,
                       addindent='',
                       newl='',
                       use_default_root_atts=True,
                       otu_label='ot:originalLabel'):
    nsv = detect_nexson_version(obj_dict)
    if not _nexson_directly_translatable_to_nexml(nsv):
        convert_nexson_format(obj_dict, DIRECT_HONEY_BADGERFISH)
        nsv = DIRECT_HONEY_BADGERFISH
    ccfg = ConversionConfig(NEXML_NEXSON_VERSION,
                            input_format=nsv,
                            use_default_root_atts=use_default_root_atts,
                            otu_label=otu_label)
    converter = Nexson2Nexml(ccfg)
    doc = converter.convert(obj_dict)
    doc.writexml(file_obj, addindent=addindent, newl=newl, encoding='utf-8')

def convert_to_nexml(obj_dict, addindent='', newl='', use_default_root_atts=True, otu_label='ot:originalLabel'):
    f, wrapper = get_utf_8_string_io_writer()
    write_obj_as_nexml(obj_dict,
                       file_obj=wrapper,
                       addindent=addindent,
                       newl=newl,
                       use_default_root_atts=use_default_root_atts,
                       otu_label=otu_label)
    flush_utf_8_writer(wrapper)
    return f.getvalue()

def resolve_nexson_format(v):
    if len(v) == 3:
        if v == '1.2':
            return BY_ID_HONEY_BADGERFISH
        if v == '1.0':
            return DIRECT_HONEY_BADGERFISH
        if v == '0.0':
            return BADGER_FISH_NEXSON_VERSION
    else:
        if v in SUPPORTED_NEXSON_VERSIONS:
            return v
    raise NotImplementedError('NexSON version "{v}" not supported.'.format(v=v))
def can_convert_nexson_forms(src_format, dest_format):
    return (dest_format in _CONVERTIBLE_FORMATS) and (src_format in _CONVERTIBLE_FORMATS)

def convert_nexson_format(blob,
                          out_nexson_format,
                          current_format=None,
                          remove_old_structs=True,
                          pristine_if_invalid=False,
                          sort_arbitrary=False):
    '''Take a dict form of NexSON and converts its datastructures to
    those needed to serialize as out_nexson_format.
    If current_format is not specified, it will be inferred.
    If `remove_old_structs` is False and different honeybadgerfish varieties
        are selected, the `blob` will be 'fat" containing both types
        of lookup structures.
    If pristine_if_invalid is False, then the object may be corrupted if it
        is an invalid nexson struct. Setting this to False can result in
        faster translation, but if an exception is raised the object may
        be polluted with partially constructed fields for the out_nexson_format.
    '''
    if not current_format:
        current_format = detect_nexson_version(blob)
    out_nexson_format = resolve_nexson_format(out_nexson_format)
    if current_format == out_nexson_format:
        if sort_arbitrary:
            sort_arbitrarily_ordered_nexson(blob)
        return blob
    two2zero = _is_by_id_hbf(out_nexson_format) and _is_badgerfish_version(current_format)
    zero2two = _is_by_id_hbf(current_format) and _is_badgerfish_version(out_nexson_format)
    if two2zero or zero2two:
        # go from 0.0 -> 1.0 then the 1.0->1.2 should succeed without nexml...
        blob = convert_nexson_format(blob,
                                     DIRECT_HONEY_BADGERFISH,
                                     current_format=current_format,
                                     remove_old_structs=remove_old_structs,
                                     pristine_if_invalid=pristine_if_invalid)
        current_format = DIRECT_HONEY_BADGERFISH
    ccdict = {'output_format':out_nexson_format,
              'input_format':current_format,
              'remove_old_structs': remove_old_structs,
              'pristine_if_invalid': pristine_if_invalid}
    ccfg = ConversionConfig(ccdict)
    if _is_badgerfish_version(current_format):
        converter = Badgerfish2DirectNexson(ccfg)
    elif _is_badgerfish_version(out_nexson_format):
        assert _is_direct_hbf(current_format)
        converter = Direct2BadgerfishNexson(ccfg)
    elif _is_direct_hbf(current_format) and (out_nexson_format == BY_ID_HONEY_BADGERFISH):
        converter = Direct2OptimalNexson(ccfg)
    elif _is_direct_hbf(out_nexson_format) and (current_format == BY_ID_HONEY_BADGERFISH):
        converter = Optimal2DirectNexson(ccfg)
    else:
        raise NotImplementedError('Conversion from {i} to {o}'.format(i=current_format, o=out_nexson_format))
    blob = converter.convert(blob)
    if sort_arbitrary:
        sort_arbitrarily_ordered_nexson(blob)
    return blob

def _recursive_sort_meta(blob, k):
    #_LOG.debug('k=' + k)
    if isinstance(blob, list):
        for i in blob:
            if isinstance(i, list) or isinstance(i, dict):
                _recursive_sort_meta(i, k)
    else:
        for inner_k, v in blob.items():
            if inner_k == 'meta' and isinstance(v, list):
                sl = []
                incd = {}
                for el in v:
                    sk = el.get('@property') or el.get('@rel') or ''
                    count = incd.setdefault(sk, 0)
                    incd[sk] = 1 + count
                    sl.append((sk, count, el))
                sl.sort()
                del v[:] # clear out the value in place
                v.extend([i[2] for i in sl]) # replace it with the item from the sorted list
            if isinstance(v, list) or isinstance(v, dict):
                _recursive_sort_meta(v, inner_k)

def sort_meta_elements(blob):
    '''For v0.0 (which has meta values in a list), this
    function recursively walks through the object
    and sorts each meta by @property or @rel values.
    '''
    v = detect_nexson_version(blob)
    if _is_badgerfish_version(v):
        _recursive_sort_meta(blob, '')
    return blob

def _inplace_sort_by_id(unsorted_list):
    '''Takes a list of dicts each of which has an '@id' key,
    sorts the elements in the list by the value of the @id key.
    Assumes that @id is unique or the dicts have a meaningul < operator
    '''
    if not isinstance(unsorted_list, list):
        return
    sorted_list = [(i.get('@id'), i) for i in unsorted_list]
    sorted_list.sort()
    del unsorted_list[:]
    unsorted_list.extend([i[1] for i in sorted_list])

def sort_arbitrarily_ordered_nexson(blob):
    '''Primarily used for testing (getting nice diffs). Calls
    sort_meta_elements and then sorts otu, node and edge list by id
    '''
    # otu, node and edge elements have no necessary orger in v0.0 or v1.0
    v = detect_nexson_version(blob)
    nex = get_nexml_el(blob)
    if _is_by_id_hbf(v):
        return blob
    sort_meta_elements(blob)
    for ob in _get_index_list_of_values(nex, 'otus'):
        _inplace_sort_by_id(ob.get('otu', []))
    for tb in _get_index_list_of_values(nex, 'trees'):
        for tree in _get_index_list_of_values(tb, 'tree'):
            _inplace_sort_by_id(tree.get('node', []))
            _inplace_sort_by_id(tree.get('edge', []))
    return blob

def add_resource_meta(obj, rel, href, version):
    if _is_badgerfish_version(version):
        m = obj.setdefault('meta', [])
        if not isinstance(m, list):
            m = [m]
            obj['meta'] = m
        m.append({'@href':href,
                  '@rel': rel,
                  '@xsi:type': 'nex:ResourceMeta'})
    else:
        k = '^' + rel
        _add_value_to_dict_bf(obj, k, {'@href': href})


def get_empty_nexson(vers='1.2.1', include_cc0=False):
    assert vers == '1.2.1'
    nexson = {
        'nexml': {
            '@about': '#study',
            '@generator': 'Open Tree API',
            '@id': 'study',
            '@nexml2json': vers,
            '@nexmljson': 'http://purl.org/opentree/nexson',
            '@version': '0.9',
            '@xmlns': {
                '$': 'http://www.nexml.org/2009',
                'nex': 'http://www.nexml.org/2009',
                'ot': 'http://purl.org/opentree-terms#',
                'xsd': 'http://www.w3.org/2001/XMLSchema#',
                'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xhtml': 'http://www.w3.org/1999/xhtml/vocab#'
            },
            '^ot:otusElementOrder': [
                'otus1',
            ],
            'otusById': {
                'otus1': {
                    'otuById':{},
                },
            },
            '^ot:treesElementOrder': [
                'trees1',
            ],
            'treesById': {
                'trees1': {
                    '@otus': 'otus1',
                    '^ot:treeElementOrder':[],
                    'treeById': {},
                },
            },
        }
    }
    # N.B. We no longer require the CC0 waiver, so we should not assume it's here
    if include_cc0:
        nexson['nexml']['^xhtml:license'] = {'@href': 'http://creativecommons.org/publicdomain/zero/1.0/'}
    return nexson

_EMPTY_TUPLE = tuple
NEWICK_NEEDING_QUOTING = re.compile(r'(\s|[\[\]():,;])')
NEXUS_NEEDING_QUOTING = re.compile(r'(\s|[-()\[\]{}/\,;:=*"`+<>])')

def quote_newick_name(s, needs_quotes_pattern=NEWICK_NEEDING_QUOTING):
    s = UNICODE(s)
    if "'" in s:
        return u"'{}'".format("''".join(s.split("'")))
    if needs_quotes_pattern.search(s):
        return u"'{}'".format(s)
    return s

def _write_newick_leaf_label(out, node, otu_group, label_key, leaf_labels, unlabeled_counter, needs_quotes_pattern):
    '''
    `label_key` is a string (a key in the otu object) or a callable that takes two arguments: the node, and the otu
    If `leaf_labels` is not None, it shoulr be a (list, dict) pair which will be filled. The list will
        hold the order encountered,
        and the dict will map name to index in the list
    '''
    otu_id = node['@otu']
    otu = otu_group[otu_id]
    if is_str_type(label_key):
        label = otu.get(label_key)
        if label is None:
            unlabeled_counter += 1
            o = otu.get('^ot:originalLabel', '<unknown>')
            label = "'*tip #{n:d} not mapped to OTT. Original label - {o}'"
            label = label.format(n=unlabeled_counter, o=o)
        else:
            label = quote_newick_name(label, needs_quotes_pattern)
    else:
        label = quote_newick_name(label_key(node, otu), needs_quotes_pattern)
    if leaf_labels is not None:
        if label not in leaf_labels[1]:
            leaf_labels[1][label] = len(leaf_labels[0])
            leaf_labels[0].append(label)
    out.write(label)
    return unlabeled_counter

def _write_newick_internal_label(out, node, otu_group, label_key, needs_quotes_pattern):
    '''`label_key` is a string (a key in the otu object) or a callable that takes two arguments: 
        the node, and the otu (which may be None for an internal node)
    If `leaf_labels` is not None, it shoulr be a (list, dict) pair which will be filled. The list will
        hold the order encountered,
        and the dict will map name to index in the list
    '''
    otu_id = node.get('@otu')
    if is_str_type(label_key):
        if otu_id is None:
            return
        otu = otu_group[otu_id]
        label = otu.get(label_key)
    else:
        label = label_key(node, None)
    if label is not None:
        label = quote_newick_name(label, needs_quotes_pattern)
        out.write(label)

def _write_newick_edge_len(out, edge):
    if edge is None:
        return
    e_len = edge.get('@length')
    if e_len is not None:
        out.write(':{e}'.format(e=e_len))

def convert_tree_to_newick(tree,
                           otu_group,
                           label_key,
                           leaf_labels,
                           needs_quotes_pattern=NEWICK_NEEDING_QUOTING,
                           subtree_id=None,
                           bracket_ingroup=False):
    '''`label_key` is a string (a key in the otu object) or a callable that takes two arguments: 
        the node, and the otu (which may be None for an internal node)
    If `leaf_labels` is not None, it shoulr be a (list, dict) pair which will be filled. The list will
        hold the order encountered,
        and the dict will map name to index in the list
    '''
    assert (not is_str_type(label_key)) or (label_key in PhyloSchema._NEWICK_PROP_VALS) #pylint: disable=W0212
    ingroup_node_id = tree.get('^ot:inGroupClade')
    if subtree_id:
        if subtree_id == 'ingroup':
            root_id = ingroup_node_id
            ingroup_node_id = None # turns of the comment pre-ingroup-marker
        else:
            root_id = subtree_id
    else:
        root_id = tree['^ot:rootNodeId']
    edges = tree['edgeBySourceId']
    if root_id not in edges:
        return None
    nodes = tree['nodeById']
    sio, out = get_utf_8_string_io_writer()
    nexson_frag_write_newick(out,
                             edges,
                             nodes,
                             otu_group,
                             label_key,
                             leaf_labels,
                             root_id,
                             needs_quotes_pattern=needs_quotes_pattern,
                             ingroup_id=ingroup_node_id,
                             bracket_ingroup=bracket_ingroup)
    flush_utf_8_writer(out)
    return sio.getvalue()

def get_subtree_otus(nexson, tree_id, subtree_id=None, return_format='otu_id'):
    assert(return_format in ['otu_id', 'ottid'])
    tree = extract_tree_nexson(nexson, tree_id)[0][1]
    ingroup_node_id = tree.get('^ot:inGroupClade')
    edges = tree['edgeBySourceId']
    nodes = tree['nodeById']
    if subtree_id:
        if subtree_id == 'ingroup':
            root_id = ingroup_node_id
        else:
            root_id = subtree_id
    else:
        root_id = tree['^ot:rootNodeId']
    if root_id not in edges:
        return None
    otuset = set()
    todo = set()
    todo.add(root_id)
    while todo:
        curr_node_id = todo.pop()
        outgoing_edges = edges.get(curr_node_id)
        if outgoing_edges is None:
            otu = nodes.get(curr_node_id).get('@otu')
            assert(otu)
            if return_format == 'otu_id':
                otuset.add(otu)
            if return_format == 'ottid':
                d = extract_otu_nexson(nexson, otu, detect_nexson_version(nexson))
                ottid = d[otu].get('^ot:ottId')
                otuset.add(ottid)
        else:
            for edge, info in outgoing_edges.items():
                todo.add(info.get('@target'))
    return(otuset)

def nexson_frag_write_newick(out,
                             edges,
                             nodes,
                             otu_group,
                             label_key,
                             leaf_labels,
                             root_id,
                             needs_quotes_pattern=NEWICK_NEEDING_QUOTING,
                             ingroup_id=None,
                             bracket_ingroup=False,
                             with_edge_lengths=True):
    '''`label_key` is a string (a key in the otu object) or a callable that takes two arguments: 
        the node, and the otu (which may be None for an internal node)
    If `leaf_labels` is not None, it shoulr be a (list, dict) pair which will be filled. The list will
        hold the order encountered,
        and the dict will map name to index in the list
    '''
    unlabeled_counter = 0
    curr_node_id = root_id
    assert curr_node_id
    curr_edge = None
    curr_sib_list = []
    curr_stack = []
    going_tipward = True
    while True:
        if going_tipward:
            outgoing_edges = edges.get(curr_node_id)
            if outgoing_edges is None:
                curr_node = nodes[curr_node_id]
                assert curr_node_id is not None
                assert curr_node_id is not None
                unlabeled_counter = _write_newick_leaf_label(out,
                                                             curr_node,
                                                             otu_group,
                                                             label_key,
                                                             leaf_labels,
                                                             unlabeled_counter,
                                                             needs_quotes_pattern)
                if with_edge_lengths:
                    _write_newick_edge_len(out, curr_edge)
                going_tipward = False
            else:
                te = [(i, e) for i, e in outgoing_edges.items()]
                te.sort() # produce a consistent rotation... Necessary?
                if bracket_ingroup and (ingroup_id == curr_node_id):
                    out.write('[pre-ingroup-marker]')
                out.write('(')
                next_p = te.pop(0)
                curr_stack.append((curr_edge, curr_node_id, curr_sib_list))
                curr_edge, curr_sib_list = next_p[1], te
                curr_node_id = curr_edge['@target']
        if not going_tipward:
            next_up_edge_id = None
            while True:
                if curr_sib_list:
                    out.write(',')
                    next_up_edge_id, next_up_edge = curr_sib_list.pop(0)
                    break
                if curr_stack:
                    curr_edge, curr_node_id, curr_sib_list = curr_stack.pop(-1)
                    curr_node = nodes[curr_node_id]
                    out.write(')')
                    _write_newick_internal_label(out,
                                                 curr_node,
                                                 otu_group,
                                                 label_key,
                                                 needs_quotes_pattern)
                    if with_edge_lengths:
                        _write_newick_edge_len(out, curr_edge)
                    if bracket_ingroup and (ingroup_id == curr_node_id):
                        out.write('[post-ingroup-marker]')
                else:
                    break
            if next_up_edge_id is None:
                break
            curr_edge = next_up_edge
            curr_node_id = curr_edge['@target']
            going_tipward = True
    out.write(';')

def _write_nexus_format(quoted_leaf_labels, tree_name_newick_list):
    if not tree_name_newick_list:
        return ''
    f, wrapper = get_utf_8_string_io_writer()
    wrapper.write('''#NEXUS
BEGIN TAXA;
    Dimensions NTax = {s};
    TaxLabels {l} ;
END;
BEGIN TREES;
'''.format(s=len(quoted_leaf_labels), l=' '.join(quoted_leaf_labels)))
    for name, newick in tree_name_newick_list:
        wrapper.write('    Tree ')
        wrapper.write(name)
        wrapper.write(' = ')
        wrapper.write(newick)
    wrapper.write('\nEND;\n')
    flush_utf_8_writer(wrapper)
    return f.getvalue()

def convert_tree(tree_id, tree, otu_group, schema, subtree_id=None):
    label_key = schema.otu_label_prop
    if schema.format_str == 'nexus':
        leaf_labels = ([], {})
        needs_quotes_pattern = NEXUS_NEEDING_QUOTING
    else:
        leaf_labels = None
        needs_quotes_pattern = NEWICK_NEEDING_QUOTING
        assert schema.format_str == 'newick'
    newick = convert_tree_to_newick(tree,
                                    otu_group,
                                    label_key,
                                    leaf_labels,
                                    needs_quotes_pattern,
                                    subtree_id=subtree_id,
                                    bracket_ingroup=schema.bracket_ingroup)
    if schema.format_str == 'nexus':
        tl = [(quote_newick_name(tree_id, needs_quotes_pattern), newick)]
        return _write_nexus_format(leaf_labels[0], tl)
    else:
        return newick

def convert_trees(tid_tree_otus_list, schema, subtree_id=None):
    label_key = schema.otu_label_prop
    if schema.format_str == 'nexus':
        leaf_labels = ([], {})
        needs_quotes_pattern = NEXUS_NEEDING_QUOTING
        conv_tree_list = []
        for tree_id, tree, otu_group in tid_tree_otus_list:
            newick = convert_tree_to_newick(tree,
                                            otu_group,
                                            label_key,
                                            leaf_labels,
                                            needs_quotes_pattern,
                                            subtree_id=subtree_id,
                                            bracket_ingroup=schema.bracket_ingroup)
            if newick:
                t = (quote_newick_name(tree_id, needs_quotes_pattern), newick)
                conv_tree_list.append(t)
        return _write_nexus_format(leaf_labels[0], conv_tree_list)
    else:
        raise NotImplementedError('convert_tree for {}'.format(schema.format_str))

def nexml_el_of_by_id(nexson, curr_version=None):
    if curr_version is None:
        curr_version = detect_nexson_version(nexson)
    if not _is_by_id_hbf(curr_version):
        nexson = convert_nexson_format(nexson, BY_ID_HONEY_BADGERFISH)
    return get_nexml_el(nexson)

def extract_otus_nexson(nexson, otus_id, curr_version=None):
    nexml_el = nexml_el_of_by_id(nexson, curr_version)
    o = nexml_el['otusById']
    if otus_id is None:
        return o
    n = o.get(otus_id)
    if n is None:
        return None
    return {otus_id: n}

def extract_otu_nexson(nexson, otu_id, curr_version=None):
    nexml_el = nexml_el_of_by_id(nexson, curr_version)
    o = nexml_el['otusById']
    if otu_id is None:
        r = {}
        for g in o.values():
            r.update(g.get('otuById', {}))
        return r
    else:
        for g in o.values():
            go = g['otuById']
            if otu_id in go:
                return {otu_id: go[otu_id]}
    return None

def cull_nonmatching_trees(nexson, tree_id, curr_version=None):
    '''Modifies `nexson` and returns it in version 1.2.1
    with any tree that does not match the ID removed.

    Note that this does not search through the NexSON for
    every node, edge, tree that was deleted. So the resulting
    NexSON may have broken references !
    '''
    if curr_version is None:
        curr_version = detect_nexson_version(nexson)
    if not _is_by_id_hbf(curr_version):
        nexson = convert_nexson_format(nexson, BY_ID_HONEY_BADGERFISH)

    nexml_el = get_nexml_el(nexson)
    tree_groups = nexml_el['treesById']
    tree_groups_to_del = []
    for tgi, tree_group in tree_groups.items():
        tbi = tree_group['treeById']
        if tree_id in tbi:
            trees_to_del = [i for i in tbi.keys() if i != tree_id]
            for tid in trees_to_del:
                tree_group['^ot:treeElementOrder'].remove(tid)
                del tbi[tid]
        else:
            tree_groups_to_del.append(tgi)
    for tgid in tree_groups_to_del:
        nexml_el['^ot:treesElementOrder'].remove(tgid)
        del tree_groups[tgid]
    return nexson

def extract_tree_nexson(nexson, tree_id, curr_version=None):
    '''Returns a list of (id, tree, otus_group) tuples for the
    specified tree_id (all trees if tree_id is None)
    '''
    if curr_version is None:
        curr_version = detect_nexson_version(nexson)
    if not _is_by_id_hbf(curr_version):
        nexson = convert_nexson_format(nexson, BY_ID_HONEY_BADGERFISH)

    nexml_el = get_nexml_el(nexson)
    tree_groups = nexml_el['treesById']
    tree_obj_otus_group_list = []
    for tree_group in tree_groups.values():
        if tree_id:
            tree_list = [(tree_id, tree_group['treeById'].get(tree_id))]
        else:
            tree_list = tree_group['treeById'].items()
        for tid, tree in tree_list:
            if tree is not None:
                otu_groups = nexml_el['otusById']
                ogi = tree_group['@otus']
                otu_group = otu_groups[ogi]['otuById']
                tree_obj_otus_group_list.append((tid, tree, otu_group))
                if tree_id is not None:
                    return tree_obj_otus_group_list
    return tree_obj_otus_group_list

def extract_tree(nexson, tree_id, schema, subtree_id=None):
    try:
        assert schema.format_str in ['newick', 'nexus']
    except:
        m = 'Only newick tree export with tip labeling as one of "{}" is currently supported'
        m = m.format('", "'.join(PhyloSchema._NEWICK_PROP_VALS))
        raise ValueError(m)
    i_t_o_list = extract_tree_nexson(nexson, tree_id, None)
    if schema.format_str == 'newick':
        tree_str_list = [convert_tree(i, t, o, schema, subtree_id=subtree_id) for i, t, o in i_t_o_list]
        tree_str_list = [i for i in tree_str_list if i is not None]
        return '\n'.join(tree_str_list)
    return convert_trees(i_t_o_list, schema, subtree_id=subtree_id)

_DEF_MESSAGES_OBJ = {"message": tuple()}
def _get_supporting_file_messages_for_this_obj(o):
    m = []
    for i in o.get('^ot:messages', _DEF_MESSAGES_OBJ).get("message", []):
        if i.get("@code") == "SUPPORTING_FILE_INFO":
            m.append(i)
    return m

def extract_supporting_file_messages(nexson):
    curr_version = detect_nexson_version(nexson)
    if not _is_by_id_hbf(curr_version):
        nexson = convert_nexson_format(nexson, BY_ID_HONEY_BADGERFISH)
    nex = nexson['nexml']
    m_list = []
    m_list.extend(_get_supporting_file_messages_for_this_obj(nex))
    for otus in nex.get('otusById', {}).values():
        m_list.extend(_get_supporting_file_messages_for_this_obj(otus))
        for otu in otus.get('otuById', {}).values():
            m_list.extend(_get_supporting_file_messages_for_this_obj(otu))
    for tree_group in nex.get('treesById', {}).values():
        m_list.extend(_get_supporting_file_messages_for_this_obj(tree_group))
        for tree in tree_group.get('treeById', {}).values():
            m_list.extend(_get_supporting_file_messages_for_this_obj(tree))
    return m_list

