#! /usr/bin/env python
from peyotl.struct_diff import DictDiff
from peyotl.utility import get_logger
import unittest
import copy

_LOG = get_logger(__name__)

class TestDictDiff(unittest.TestCase):

    def testEqualDiff(self):
        a = {'some': ['dict'],
             'with': 'some',
             'key':{'s': 'that',
                    'are': ['nes', 'ted']}}
        b = dict(a)
        self.assertEqual(None, DictDiff.create(a, b))

    def testAddDelDiff(self):
        a = {'some': ['dict'],
             'with': 'some',
             'key':{'s': 'that',
                    'are': ['nes', 'ted']}}
        b = dict(a)
        b['extra'] = 'cool stuff'
        ddo_a = DictDiff.create(a, b)
        add_str = ddo_a.additions_expr(par='obj')
        self.assertEqual(add_str, ["obj['extra'] = 'cool stuff'"])
        self.assertEqual([], ddo_a.deletions_expr(par='o'))
        self.assertEqual([], ddo_a.modification_expr(par='o'))
        ddo_d = DictDiff.create(b, a)
        add_str = ddo_d.deletions_expr(par='obj')
        self.assertEqual(add_str, ["del obj['extra']"])
        self.assertEqual([], ddo_d.additions_expr(par='o'))
        self.assertEqual([], ddo_d.modification_expr(par='o'))
        c_a = copy.deepcopy(a)
        self.assertEqual(a, c_a)
        c_b = copy.deepcopy(b)
        self.assertEqual(b, c_b)
        ddo_a.patch(c_a)
        self.assertEqual(b, c_a)
        ddo_d.patch(c_b)
        self.assertEqual(a, c_b)

    def testAddModDelDiff(self):
        a = {'some': ['dict'],
             'with': 'some',
             'key':{'s': 'that',
                    'are': ['nes', 'ted']}}
        b = dict(a)
        b['extra'] = 'cool stuff'
        b['with'] = 'new stuff'
        del b['some']
        ddo_a = DictDiff.create(a, b)
        add_str = ddo_a.additions_expr(par='obj')
        self.assertEqual(add_str, ["obj['extra'] = 'cool stuff'"])
        self.assertEqual(["del obj['some']"], ddo_a.deletions_expr(par='obj'))
        self.assertEqual(["obj['with'] = 'new stuff'"], ddo_a.modification_expr(par='obj'))
        ddo_d = DictDiff.create(b, a)
        self.assertEqual(ddo_d.deletions_expr(par='obj'), ["del obj['extra']"])
        self.assertEqual(["obj['some'] = ['dict']"], ddo_d.additions_expr(par='obj'))
        self.assertEqual(["obj['with'] = 'some'"], ddo_d.modification_expr(par='obj'))
        c_a = copy.deepcopy(a)
        self.assertEqual(a, c_a)
        c_b = copy.deepcopy(b)
        self.assertEqual(b, c_b)
        ddo_a.patch(c_a)
        self.assertEqual(b, c_a)
        ddo_d.patch(c_b)
        self.assertEqual(a, c_b)

    def testSecondLevelAddModDelDiff(self):
        a = {'some': ['dict'],
             'with': 'some',
             'key':{'s': 'that',
                    'are': ['nes', 'ted']}}
        b = copy.deepcopy(a)
        b['key']['a'] = 'cool stuff'
        b['key']['s'] = 'this'
        del b['key']['are']
        ddo_a = DictDiff.create(a, b)
        self.assertEqual(ddo_a.additions_expr(par='obj'), [])
        self.assertEqual([], ddo_a.deletions_expr(par='obj'))
        self.assertEqual(["obj['key']['a'] = 'cool stuff'",
                          "del obj['key']['are']",
                          "obj['key']['s'] = 'this'",
                          ], ddo_a.modification_expr(par='obj'))
        ddo_d = DictDiff.create(b, a)
        self.assertEqual(ddo_d.deletions_expr(par='obj'), [])
        self.assertEqual([], ddo_d.additions_expr(par='obj'))
        self.assertEqual(["obj['key']['are'] = ['nes', 'ted']",
                          "del obj['key']['a']",
                          "obj['key']['s'] = 'that'",
                          ], ddo_d.modification_expr(par='obj'))
        c_a = copy.deepcopy(a)
        self.assertEqual(a, c_a)
        c_b = copy.deepcopy(b)
        self.assertEqual(b, c_b)
        ddo_a.patch(c_a)
        self.assertEqual(b, c_a)
        ddo_d.patch(c_b)
        self.assertEqual(a, c_b)

    def testListAddModDelDiff(self):
        a = {'some': ['dict', 'bool'],
             'with': 'some',
             'key':{'s': 'that',
                    'are': ['nes', 'ted']}}
        b = copy.deepcopy(a)
        b['some'][0] = 'list'
        b['some'].append('last')
        ddo_a = DictDiff.create(a, b)
        self.assertEqual(ddo_a.additions_expr(par='obj'), [])
        self.assertEqual([], ddo_a.deletions_expr(par='obj'))
        self.assertEqual(["obj['some'][0] = 'list'",
                          "obj['some'].insert(2, 'last')"
                         ], ddo_a.modification_expr(par='obj'))
        ddo_d = DictDiff.create(b, a)
        self.assertEqual(ddo_d.deletions_expr(par='obj'), [])
        self.assertEqual([], ddo_d.additions_expr(par='obj'))
        self.assertEqual(["obj['some'][0] = 'dict'",
                          "obj['some'].pop(2)"
                         ], ddo_d.modification_expr(par='obj'))
        c_a = copy.deepcopy(a)
        self.assertEqual(a, c_a)
        c_b = copy.deepcopy(b)
        self.assertEqual(b, c_b)
        ddo_a.patch(c_a)
        self.assertEqual(b, c_a)
        ddo_d.patch(c_b)
        self.assertEqual(a, c_b)

if __name__ == "__main__":
    unittest.main()
