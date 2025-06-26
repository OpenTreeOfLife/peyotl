#!/usr/bin/env python
from __future__ import absolute_import, print_function, division


class DictDiff(object):
    def __init__(self):
        self._additions = []
        self._deletions = []
        self._modifications = []

    def finish(self):
        self._additions.sort()
        self._deletions.sort()
        self._modifications.sort()

    def edits_expr(self, par=''):
        r = self.additions_expr(par=par)
        r.extend(self.deletions_expr(par=par))
        r.extend(self.modification_expr(par=par))
        return r

    def additions_expr(self, par=''):
        r = []
        for k, v in self._additions:
            s = '{p}[{k}] = {v}'.format(p=par, k=repr(k), v=repr(v))
            r.append(s)
        return r

    def modification_expr(self, par=''):
        r = []
        for k, v in self._modifications:
            pk = '{p}[{k}]'.format(p=par, k=repr(k))
            if isinstance(v, DictDiff) or isinstance(v, ListDiff):
                sedits = v.edits_expr(par=pk)
                r.extend(sedits)
            else:
                s = '{pk} = {v}'.format(pk=pk, v=repr(v))
                r.append(s)
        return r

    def deletions_expr(self, par=''):
        r = []
        for deletion in self._deletions:
            k = deletion[0]
            s = 'del {p}[{k}]'.format(p=par, k=repr(k))
            r.append(s)
        return r

    def add_addition(self, k, v):
        self._additions.append((k, v))

    def add_deletion(self, k, v):
        self._deletions.append((k, v))

    def add_modification(self, k, v):
        self._modifications.append((k, v))

    def patch(self, src):
        for k, v in self._deletions:
            del src[k]
        for k, v in self._additions:
            src[k] = v
        for k, v in self._modifications:
            if isinstance(v, DictDiff) or isinstance(v, ListDiff):
                v.patch(src[k])
            else:
                src[k] = v

    @staticmethod
    def create(src, dest, **kwargs):
        """Inefficient comparison of src and dest dicts.
        Recurses through dict and lists.
        returns None if there is no difference and a
        DictDiffObject of there are differences
        **kwargs can contain:
            wrap_dict_in_list default False. If True and one
                value is present as a list and the other is
                a dict, then the dict will be converted to
                a list of one dict of the comparison. This
                is helpful given the BadgerFish convention of
                emitting single elements as a dict, but >1 elements
                as a list of dicts:
        """
        if src == dest:
            return None
        ddo = DictDiff()
        sk = set(src.keys())
        dk = set(dest.keys())
        for k in sk:
            v = src[k]
            if k in dk:
                dv = dest[k]
                if v != dv:
                    rec_call = None
                    if isinstance(v, dict) and isinstance(dv, dict):
                        rec_call = DictDiff.create(v, dv, **kwargs)
                    elif isinstance(v, list) and isinstance(dv, list):
                        rec_call = ListDiff.create(v, dv, **kwargs)
                    elif kwargs.get('wrap_dict_in_list', False):
                        if isinstance(v, dict) and isinstance(dv, list):
                            rec_call = ListDiff.create([v], dv, **kwargs)
                        elif isinstance(dv, dict) or isinstance(v, list):
                            rec_call = ListDiff.create(v, [dv], **kwargs)
                    if rec_call is not None:
                        ddo.add_modification(k, rec_call)
                    else:
                        ddo.add_modification(k, dv)
            else:
                ddo.add_deletion(k, v)
        add_keys = dk - sk
        for k in add_keys:
            ddo.add_addition(k, dest[k])
        ddo.finish()
        return ddo


class ListDiff(object):
    def __init__(self):
        self._additions = []
        self._modifications = []
        self._deletions = []

    @staticmethod
    def create(src, dest, **kwargs):
        """Inefficient comparison of src and dest dicts.
        Recurses through dict and lists.
        returns (is_identical, modifications, additions, deletions)
        where each
            is_identical is a boolean True if the dicts have
                contents that compare equal.
        and the other three are dicts:
            attributes both, but with different values
            attributes in dest but not in src
            attributes in src but not in dest

        Returned dicts may alias objects in src, and dest
        """
        if src == dest:
            return None
        trivial_order = [(i, i) for i in range(min(len(src), len(dest)))]
        optimal_order = trivial_order
        src_ind = 0
        dest_ind = 0
        add_offset = 0
        num_deletions = 0
        diffs = ListDiff()
        for p in optimal_order:
            ns, nd = p
            while src_ind < ns:
                diffs.add_deletion(src_ind, src[src_ind])
                src_ind += 1
                num_deletions += 1
            while dest_ind < nd:
                diffs.add_insertion(src_ind - num_deletions, add_offset, dest[dest_ind])
                dest_ind += 1
                add_offset += 1
            sv, dv = src[ns], dest[nd]
            if sv != dv:
                rec_call = None
                if isinstance(sv, dict) and isinstance(dv, dict):
                    rec_call = DictDiff.create(sv, dv, **kwargs)
                elif isinstance(sv, list) and isinstance(dv, list):
                    rec_call = ListDiff.create(sv, dv, **kwargs)
                elif kwargs.get('wrap_dict_in_list', False):
                    if isinstance(sv, dict) and isinstance(dv, list):
                        rec_call = ListDiff.create([sv], dv, **kwargs)
                    elif isinstance(dv, dict) or isinstance(sv, list):
                        rec_call = ListDiff.create(sv, [dv], **kwargs)
                if rec_call is not None:
                    diffs.add_modificaton(src_ind, rec_call)
                else:
                    diffs.add_modificaton(src_ind, (sv, dv))
            src_ind += 1
            dest_ind += 1
        while src_ind < len(src):
            diffs.add_deletion(src_ind, src[src_ind])
            src_ind += 1
        while dest_ind < len(dest):
            diffs.add_insertion(src_ind, add_offset, dest[dest_ind])
            dest_ind += 1
            add_offset += 1
        diffs.finish()
        return diffs

    def edits_expr(self, par=''):
        r = self.modification_expr(par=par)
        r.extend(self.deletions_expr(par=par))
        r.extend(self.additions_expr(par=par))
        return r

    def additions_expr(self, par=''):
        r = []
        for k, ld in self._additions:
            post_del_ind = k[0] + k[1]
            v = ld.obj
            s = '{p}.insert({k:d}, {v})'.format(p=par, k=post_del_ind, v=repr(v))
            r.append(s)
        return r

    def modification_expr(self, par=''):
        r = []
        for k, le in self._modifications:
            v = le.obj
            pk = '{p}[{k}]'.format(p=par, k=repr(k))
            if isinstance(v, DictDiff) or isinstance(v, ListDiff):
                sedits = v.edits_expr(par=pk)
                r.extend(sedits)
            else:
                s = '{pk} = {v}'.format(pk=pk, v=repr(v[1]))
                r.append(s)
        return r

    def deletions_expr(self, par=''):
        # _deletions are reverse sorted
        r = []
        for deletion in self._deletions:
            k = deletion[0]
            s = '{p}.pop({k:d})'.format(p=par, k=k)
            r.append(s)
        return r

    def patch(self, src):
        for k, lem in self._modifications:
            v = lem.obj
            if isinstance(v, DictDiff) or isinstance(v, ListDiff):
                v.patch(src[k])
            else:
                dest = v[1]
                src[k] = dest
        for k, v in self._deletions:
            src.pop(k)
        for k, ld in self._additions:
            post_del_ind = k[0] + k[1]
            v = ld.obj
            src.insert(post_del_ind, v)

    def add_deletion(self, ind, obj):
        tup = (ind, ListDeletion(ind, obj))
        self._deletions.append(tup)

    def add_insertion(self, ind, add_offset, obj):
        sortable_key = (ind, add_offset)
        tup = (sortable_key, ListAddition(ind, add_offset, obj))
        self._additions.append(tup)

    def add_modificaton(self, ind, obj):
        tup = (ind, ListElModification(ind, obj))
        self._modifications.append(tup)

    def finish(self):
        self._modifications.sort()
        self._deletions.sort(reverse=True)
        self._additions.sort()


class ListEdit(object):
    def __init__(self, src_ind, obj):
        self.src_index = src_ind
        self.obj = obj


class ListDeletion(ListEdit):
    def __init__(self, src_ind, obj):
        ListEdit.__init__(self, src_ind, obj)

    def __repr__(self):
        return 'ListDeletion({s}, {o})'.format(s=self.src_index, o=repr(self.obj))

    def __str__(self):
        return repr(self)


class ListAddition(ListEdit):
    def __init__(self, src_ind, add_offset, obj):
        ListEdit.__init__(self, src_ind, obj)
        self.add_offset = add_offset

    def __repr__(self):
        return 'ListAddition({s}, {o})'.format(s=self.src_index, o=repr(self.obj))

    def __str__(self):
        return repr(self)


class ListElModification(ListEdit):
    def __init__(self, src_ind, obj):
        ListEdit.__init__(self, src_ind, obj)

    def __repr__(self):
        return 'ListElModification({s}, {o})'.format(s=self.src_index,
                                                     o=repr(self.obj))

    def __str__(self):
        return repr(self)
