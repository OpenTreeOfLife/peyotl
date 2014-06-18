#!/usr/bin/env python
from peyotl import get_logger
_LOG = get_logger(__name__)

def find_intervening_fragments(input_str,
                               expected_str_list,
                               start_pos=0,
                               case_sensitive=False,
                               template_i=None,
                               curr_word_ind=0,
                               curr_result=None):
    '''Returns a list of lists of prefixes, intervening fragments, and suffixes
    that are in input_str but not expected_str_list.
    the length of the returned list will be one longer that the length of expected_str_list

    Returns None if input_str does not contain the fragments in expected_str_list

    r = find_intervening_fragments(x, y, case_sensitive=True)
    if r is not None:
        for possible in r:
            z = [possible[0]]
            for i in range(1:len(possible)):
                z.append(y[i -1])
                z.append(possible[i])
            assert ''.join(z) == x
    '''
    last_ind = len(input_str) - sum([len(i) for i in expected_str_list])
    if last_ind < 0:
        return None
    if case_sensitive:
        istr, elist = input_str, expected_str_list
        if template_i is None:
            template_i = istr
    else:
        istr = input_str.lower()
        expected_str_list = [i.lower() for i in expected_str_list]
        if template_i is None:
            template_i = input_str
    try:
        curr_word = expected_str_list[curr_word_ind]
    except IndexError:
        return None
    noff = istr.find(curr_word, start_pos)
    #_LOG.debug('{c} at {n} of {t} (called with start_pos={s})'.format(c=curr_word, n=noff, t=template_i, s=start_pos))
    if noff < 0:
        return None
    if noff < last_ind:
        #_LOG.debug('one match found. checking tail...')
        tail_results = find_intervening_fragments(istr,
                                                  expected_str_list,
                                                  start_pos=1+noff,
                                                  case_sensitive=True, 
                                                  template_i=template_i,
                                                  curr_word_ind=curr_word_ind)
    else:
        tail_results = None
    if curr_result is None:
        curr_result = [template_i[:noff]]
    else:
        curr_result = list(curr_result) # make a copy because this is recursive
        curr_result.append(template_i[start_pos:noff])
    #_LOG.debug('curr_result = {x}'.format(x=repr(curr_result)))
    curr_word_ind += 1
    offset = noff + len(curr_word)
    if curr_word_ind >= len(expected_str_list):
        curr_result.append(template_i[offset:])
        boxed_cr = [curr_result]
        if tail_results is not None:
            boxed_cr.extend(tail_results)
        return boxed_cr
    #_LOG.debug('more words found. continuing check...')
    continued_results = find_intervening_fragments(istr,
                                                   expected_str_list,
                                                   start_pos=offset,
                                                   case_sensitive=True, 
                                                   template_i=template_i,
                                                   curr_word_ind=curr_word_ind,
                                                   curr_result=curr_result)
    if continued_results is None:
        return tail_results
    if tail_results is not None:
        continued_results.extend(tail_results)
    return continued_results

