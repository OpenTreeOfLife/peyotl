from peyotl.utility import get_logger, get_config_setting_kwargs, write_to_filepath
from peyotl.phylesystem.helper import DIGIT_PATTERN, create_id2study_info, diagnose_repo_study_id_convention
from peyotl.utility.input_output import read_as_json, write_as_json
import json
try:
    import anyjson
except:
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads
from peyotl.phylesystem.git_actions import GitAction, ID_PATTERN
from peyotl.nexson_syntax import detect_nexson_version
import codecs
import os
import re
from threading import Lock


_LOG = get_logger(__name__)
class PhylesystemShardBase(object):
    def __init__(self, name):
        self._index_lock = Lock()
        self._study_index = {}
        self.name = name
        self.path = ''
        self.has_aliases = False
    #pylint: disable=E1101
    def get_rel_path_fragment(self, study_id):
        '''For `study_id` returns the path from the
        repo to the study file. This is useful because
        (if you know the remote), it lets you construct the full path.
        '''
        with self._index_lock:
            r = self._study_index[study_id]
        fp = r[-1]
        return fp[(len(self.path) + 1):] # "+ 1" to remove the /
    @property
    def study_index(self):
        return self._study_index
    def get_study_ids(self, include_aliases=False):
        with self._index_lock:
            k = self._study_index.keys()
        if self.has_aliases and (not include_aliases):
            x = []
            for i in k:
                if DIGIT_PATTERN.match(i) or ((len(i) > 1) and (i[-2] == '_')):
                    pass
                else:
                    x.append(i)
            return x
        return list(k)

class PhylesystemShardProxy(PhylesystemShardBase):
    '''Proxy for shard when interacting with external resources if given the configuration of a remote Phylesystem
    '''
    def __init__(self, config):
        PhylesystemShardBase.__init__(self, config['name'])
        # ' ' mimics place of the abspath of repo in path -> relpath mapping
        self.path = ' '
        self._index_lock = Lock()
        self.name = config['name']
        self.repo_nexml2json = config['repo_nexml2json']
        self.has_aliases = False
        d = {}
        for study in config['studies']:
            kl = study['keys']
            if len(kl) > 1:
                self.has_aliases = True
            for k in study['keys']:
                d[k] = (self.name, self.path, self.path + '/study/' + study['relpath'])
        self._study_index = d

class PhylesystemShard(PhylesystemShardBase):
    '''Wrapper around a git repos holding nexson studies'''
    def __init__(self,
                 name,
                 path,
                 repo_nexml2json=None,
                 git_ssh=None,
                 pkey=None,
                 git_action_class=GitAction,
                 push_mirror_repo_path=None,
                 new_study_prefix=None,
                 infrastructure_commit_author='OpenTree API <api@opentreeoflife.org>',
                 **kwargs):
        self._index_lock = Lock()
        PhylesystemShardBase.__init__(self, name)
        self._infrastructure_commit_author = infrastructure_commit_author
        self._study_counter_lock = Lock()
        self._master_branch_repo_lock = Lock()
        self._new_study_prefix = new_study_prefix
        self._ga_class = git_action_class
        self.git_ssh = git_ssh
        self.pkey = pkey
        path = os.path.abspath(path)
        dot_git = os.path.join(path, '.git')
        study_dir = os.path.join(path, 'study')
        if not os.path.isdir(path):
            raise ValueError('"{p}" is not a directory'.format(p=path))
        if not os.path.isdir(dot_git):
            raise ValueError('"{p}" is not a directory'.format(p=dot_git))
        if not os.path.isdir(study_dir):
            raise ValueError('"{p}" is not a directory'.format(p=study_dir))
        self.path = path
        self._id_minting_file = os.path.join(path, 'next_study_id.json')
        if self._new_study_prefix is None:
            prefix_file = os.path.join(path, 'new_study_prefix')
            if os.path.exists(prefix_file):
                pre_content = open(prefix_file, 'r').read().strip()
                valid_pat = re.compile('^[a-zA-Z0-9]+_$')
                if len(pre_content) != 3 or not valid_pat.match(pre_content):
                    raise ValueError('Expecting prefix in new_study_prefix file to be two '\
                                     'letters followed by an underscore')
                self._new_study_prefix = pre_content
            else:
                self._new_study_prefix = 'ot_' # ot_ is the default if there is no file
        d = create_id2study_info(study_dir, name)
        rc_dict = diagnose_repo_study_id_convention(path)
        self.filepath_for_study_id_fn = rc_dict['fp_fn']
        self.filepath_for_global_resource_fn = lambda frag: os.path.join(path, frag)
        self.id_alias_list_fn = rc_dict['id2alias_list']
        if rc_dict['convention'] != 'simple':
            a = {}
            for k, v in d.items():
                alias_list = self.id_alias_list_fn(k)
                for alias in alias_list:
                    a[alias] = v
            d = a
            self.has_aliases = True
            self.inferred_study_prefix = True
            self.infer_study_prefix()
        else:
            self.inferred_study_prefix = False
        self.study_dir = study_dir
        with self._index_lock:
            self._locked_refresh_study_ids()
        self.parent_path = os.path.split(path)[0] + '/'
        self.git_dir = dot_git
        self.push_mirror_repo_path = push_mirror_repo_path
        if repo_nexml2json is None:
            try:
                repo_nexml2json = get_config_setting_kwargs(None, 'phylesystem', 'repo_nexml2json', **kwargs)
            except:
                pass
            if repo_nexml2json == None:
                repo_nexml2json = self.diagnose_repo_nexml2json()
        self.repo_nexml2json = repo_nexml2json
        self._next_study_id = None
        self._study_counter_lock = None
        self._known_prefixes = None
    @property
    def known_prefixes(self):
        if self._known_prefixes is None:
            self._known_prefixes = self._diagnose_prefixes()
        return self._known_prefixes
    @property
    def new_study_prefix(self):
        return self._new_study_prefix
    def _diagnose_prefixes(self):
        '''Returns a set of all of the prefixes seen in the study dir
        '''
        p = set()
        for name in os.listdir(self.study_dir):
            if ID_PATTERN.match(name):
                p.add(name[:3])
        return p

    def _locked_refresh_study_ids(self):
        d = create_id2study_info(self.study_dir, self.name)
        rc_dict = diagnose_repo_study_id_convention(self.path)
        self.filepath_for_study_id_fn = rc_dict['fp_fn']
        self.id_alias_list_fn = rc_dict['id2alias_list']
        if rc_dict['convention'] != 'simple':
            a = {}
            for k, v in d.items():
                alias_list = self.id_alias_list_fn(k)
                for alias in alias_list:
                    a[alias] = v
            d = a
            self.has_aliases = True
        else:
            self.has_aliases = False
        self._study_index = d
    def infer_study_prefix(self):
        prefix_file = os.path.join(self.path, 'new_study_prefix')
        if os.path.exists(prefix_file):
            pre_content = open(prefix_file, 'rU').read().strip()
            valid_pat = re.compile('^[a-zA-Z0-9]+_$')
            if len(pre_content) != 3 or not valid_pat.match(pre_content):
                raise ValueError('Expecting prefix in new_study_prefix file to be two '\
                                 'letters followed by an underscore')
            self._new_study_prefix = pre_content
        else:
            self._new_study_prefix = 'ot_' # ot_ is the default if there is no file

    def register_new_study(self, study_id):
        pass

    def delete_study_from_index(self, study_id):
        alias_list = self.id_alias_list_fn(study_id)
        with self._index_lock:
            for i in alias_list:
                try:
                    del self._study_index[i]
                except:
                    pass

    def _determine_next_study_id(self):
        """Return the numeric part of the newest study_id

        Checks out master branch as a side effect!"""
        if self._study_counter_lock is None:
            self._study_counter_lock = Lock()
        prefix = self._new_study_prefix
        lp = len(prefix)
        n = 0
        # this function holds the lock for quite awhile,
        #   but it only called on the first instance of
        #   of creating a new study
        with self._study_counter_lock:
            with self._index_lock:
                for k in self._study_index.keys():
                    if k.startswith(prefix):
                        try:
                            pn = int(k[lp:])
                            if pn > n:
                                n = pn
                        except:
                            pass
            nsi_contents = self._read_master_branch_resource(self._id_minting_file, is_json=True)
            if nsi_contents:
                self._next_study_id = nsi_contents['next_study_id']
                if self._next_study_id <= n:
                    m = 'next_study_id in {} is set lower than the ID of an existing study!'
                    m = m.format(self._id_minting_file)
                    raise RuntimeError(m)
            else:
                # legacy support for repo with no next_study_id.json file
                self._next_study_id = n
                self._advance_new_study_id() # this will trigger the creation of the file
    def _read_master_branch_resource(self, fn, is_json=False):
        '''This will force the current branch to master! '''
        with self._master_branch_repo_lock:
            ga = self._create_git_action_for_global_resource()
            with ga.lock():
                ga.checkout_master()
                if os.path.exists(fn):
                    if is_json:
                        return read_as_json(fn)
                    return codecs.open(fn, 'rU', encoding='utf-8').read()
                return None
    def _write_master_branch_resource(self, content, fn, commit_msg, is_json=False):
        '''This will force the current branch to master! '''
        #TODO: we might want this to push, but currently it is only called in contexts in which
        # we are about to push any way (study creation)
        with self._master_branch_repo_lock:
            ga = self._create_git_action_for_global_resource()
            with ga.lock():
                ga.checkout_master()
                if is_json:
                    write_as_json(content, fn)
                else:
                    write_to_filepath(content, fn)
                ga._add_and_commit(fn, self._infrastructure_commit_author, commit_msg)
    @property
    def next_study_id(self):
        return self._next_study_id
    def diagnose_repo_nexml2json(self):
        with self._index_lock:
            fp = self.study_index.values()[0][2]
        _LOG.debug('diagnose_repo_nexml2json with fp={}'.format(fp))
        with codecs.open(fp, mode='r', encoding='utf-8') as fo:
            fj = json.load(fo)
            return detect_nexson_version(fj)

    def _create_git_action_for_global_resource(self):
        return self._ga_class(repo=self.path,
                              git_ssh=self.git_ssh,
                              pkey=self.pkey,
                              path_for_study_fn=self.filepath_for_global_resource_fn)
    def create_git_action(self):
        return self._ga_class(repo=self.path,
                              git_ssh=self.git_ssh,
                              pkey=self.pkey,
                              path_for_study_fn=self.filepath_for_study_id_fn)
    def pull(self, remote='origin', branch_name='master'):
        with self._index_lock:
            ga = self.create_git_action()
            from peyotl.phylesystem.git_workflows import _pull_gh
            _pull_gh(ga, remote, branch_name)
            self._locked_refresh_study_ids()
    def _advance_new_study_id(self):
        ''' ASSUMES the caller holds the _study_counter_lock !
        Returns the current numeric part of the next study ID, advances
        the counter to the next value, and stores that value in the
        file in case the server is restarted.
        '''
        c = self._next_study_id
        self._next_study_id = 1 + c
        content = u'{"next_study_id": %d}\n' % self._next_study_id
        # The content is JSON, but we hand-rolled the string above
        #       so that we can use it as a commit_msg
        self._write_master_branch_resource(content,
                                           self._id_minting_file,
                                           commit_msg=content,
                                           is_json=False)
        return c
    def _mint_new_study_id(self):
        '''Checks out master branch as a side effect'''
        # studies created by the OpenTree API start with ot_,
        # so they don't conflict with new study id's from other sources
        with self._study_counter_lock:
            c = self._advance_new_study_id()
        #@TODO. This form of incrementing assumes that
        #   this codebase is the only service minting
        #   new study IDs!
        return "{p}{c:d}".format(p=self._new_study_prefix, c=c)

    def create_git_action_for_new_study(self, new_study_id=None):
        '''Checks out master branch as a side effect'''
        ga = self.create_git_action()
        if new_study_id is None:
            new_study_id = self._mint_new_study_id()
        fp = ga.path_for_study(new_study_id)
        with self._index_lock:
            self._study_index[new_study_id] = (self.name, self.study_dir, fp)
        return ga, new_study_id

    def _create_git_action_for_mirror(self):
        mirror_ga = self._ga_class(repo=self.push_mirror_repo_path,
                                   git_ssh=self.git_ssh,
                                   pkey=self.pkey,
                                   path_for_study_fn=self.filepath_for_study_id_fn)
        return mirror_ga

    def push_to_remote(self, remote_name):
        if self.push_mirror_repo_path is None:
            raise RuntimeError('This PhylesystemShard has no push mirror, so it cannot push to a remote.')
        working_ga = self.create_git_action()
        mirror_ga = self._create_git_action_for_mirror()
        with mirror_ga.lock():
            with working_ga.lock():
                mirror_ga.fetch(remote='origin')
            mirror_ga.merge('origin/master', destination='master')
            mirror_ga.push(branch='master',
                           remote=remote_name)
        return True

    def _is_alias(self, study_id):
        alias_list = self.id_alias_list_fn(study_id)
        if len(alias_list) > 1:
            ml = max([len(i) for i in alias_list])
            if ml > len(study_id):
                return True
        return False

    def iter_study_filepaths(self, **kwargs): #pylint: disable=W0613
        '''Returns a pair: (study_id, absolute filepath of study file)
        for each study in this repository.
        Order is arbitrary.
        '''
        with self._index_lock:
            for study_id, info in self._study_index.items():
                if not self._is_alias(study_id):
                    yield study_id, info[-1]

    def iter_study_objs(self, **kwargs):
        '''Returns a pair: (study_id, nexson_blob)
        for each study in this repository.
        Order is arbitrary.
        '''
        for study_id, fp in self.iter_study_filepaths(**kwargs):
            if not self._is_alias(study_id):
                with codecs.open(fp, 'r', 'utf-8') as fo:
                    try:
                        nex_obj = anyjson.loads(fo.read())
                        yield (study_id, nex_obj)
                    except Exception:
                        pass

    def write_configuration(self, out, secret_attrs=False):
        key_order = ['name', 'path', 'git_dir', 'study_dir', 'repo_nexml2json',
                     'git_ssh', 'pkey', 'has_aliases', '_next_study_id',
                     'number of studies']
        cd = self.get_configuration_dict(secret_attrs=secret_attrs)
        for k in key_order:
            if k in cd:
                out.write('  {} = {}'.format(k, cd[k]))
        out.write('  studies in alias groups:\n')
        for o in cd['studies']:
            out.write('    {} ==> {}\n'.format(o['keys'], o['relpath']))

    def get_configuration_dict(self, secret_attrs=False):
        rd = {'name': self.name,
              'path': self.path,
              'git_dir': self.git_dir,
              'repo_nexml2json': self.repo_nexml2json,
              'study_dir': self.study_dir,
              'git_ssh': self.git_ssh, }
        if self._next_study_id is not None:
            rd['_next_study_id'] = self._next_study_id,
        if secret_attrs:
            rd['pkey'] = self.pkey
        with self._index_lock:
            si = self._study_index
        r = _invert_dict_list_val(si)
        key_list = list(r.keys())
        rd['number of studies'] = len(key_list)
        key_list.sort()
        m = []
        for k in key_list:
            v = r[k]
            fp = k[2]
            assert fp.startswith(self.study_dir)
            rp = fp[len(self.study_dir) + 1:]
            m.append({'keys': v, 'relpath': rp})
        rd['studies'] = m
        return rd
    def get_branch_list(self):
        ga = self.create_git_action()
        return ga.get_branch_list()
    def get_changed_studies(self, ancestral_commit_sha, study_ids_to_check=None):
        ga = self.create_git_action()
        return ga.get_changed_studies(ancestral_commit_sha, study_ids_to_check=study_ids_to_check)

def _invert_dict_list_val(d):
    o = {}
    for k, v in d.items():
        o.setdefault(v, []).append(k)
    for v in o.values():
        v.sort()
    return o

