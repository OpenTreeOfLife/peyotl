#!/usr/bin/env python
from peyotl import write_as_json
import codecs
import json
import time

def report_results(tag, duration, expected_fn, result):
    expected = json.load(codecs.open(expected_fn, 'rU', encoding='utf-8'))
    succeeded = True
    if expected != result:
        obtained_fn = expected_fn + '-obtained.json'
        write_as_json(result, obtained_fn)
        succeeded = False
    return {'tag': tag,
            'duration': duration,
            'expected-output':succeeded,
            'returned': True,
            'status': 200
           }

def report_error(tag, duration, err):
    r = {'tag': tag,
            'duration': duration,
            'expected-output':False,
            'returned': False,
            'returned': True,
            'status': err.response.status_code,
            'url': err.response.url,
            }
    if err.response.text:
        r['content'] = err.response.text
    return r


def _ot_call(tag, expected_fn, func, *valist, **kwargs):
    try:
        start_t = time.time()
        result = func(*valist, **kwargs)
        end_t = time.time()
        summ = report_results(tag, end_t - start_t, expected_fn, result)
    except HTTPError, x:
        end_t = time.time()
        summ = report_error(tag, end_t - start_t, x)
    summary_list.append(summ)

if __name__ == '__main__':
    from peyotl.api import APIWrapper
    from requests import HTTPError
    otwrap = APIWrapper()
    summary_list = []

    summary = _ot_call('treemachine/getSyntheticTree',
                       'curl-versions/getSyntheticTree.json',
                       otwrap.treemachine.get_synthetic_tree,
                       'otol.draft.22',
                       format='arguson',
                       node_id=3534540,
                       max_depth=3)
    summary_list.append(summary)
    print summary_list
