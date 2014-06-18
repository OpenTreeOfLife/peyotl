#!/usr/bin/env python
import re
from peyotl import get_logger
_LOG = get_logger(__name__)

class FragType:
    EMPTY = 0
    HIGHER_TAXON_CASE_S = 1
    TAXON_CASE_I = 2
    EPITHET_CASE_S = 3
    GENBANK_ACCESSION = 4
    VAR = 5
    SP = 6
    SSP = 7
    CF = 8
    AFF = 9
    SPACE = 10
    WHITESPACE = 11
    PUNCTUATION = 12
    NUMBER = 12
    UC_LETTER = 13
    LC_LETTER = 14
    START = 15
    END = 16
_HIGHER_TAXON_CS = '([-A-Z][a-z]{2,})'
_TAXON_CI = '([-A-Za-z]{3,})'
_EPITHET_CS = '([[-a-z]{3,})'
_GENBANK = '([A-Z]{1,2}[0-9]{5,6})'
_VAR = '([vV][aA][rR]\.?)'
_SP = '([sS][pP]\.?)'
_SSP = '([sS][sS][pP]\.?)'
_CF = '([cC][fF]\.?)'
_AFF = '([aA][fF][fF]\.?)'


class OTULabelStringCruncher(object):
    def __init__(self, pat_list):
        self.pat_list = pat_list
        self.gb_accession_index = None
        for n, p in pat_list[1:-1:2]:
            if p['code'] == FragType.GENBANK_ACCESSION:
                self.gb_accession_index = (n - 1)/2 # each odd-indexed pattern will have one group
        self.pattern = ''.join(pat_list)

def _matches_all(word_list, pat):
    for word in word_list:
        if not pat.match(word):
            return False
    return True

def attempt_to_create_taxonomic_regex_from_words(word_list, is_first):
    '''Takes a series of words assumed to be taxonomic name fragments
    returns a dict with:
        `regex` : pattern with a group to capture the name
        code: a facet of the FragType enum
        '''
    if not isinstance(word_list, set):
        word_list = set(word_list)
    if is_first:
        if _matches_all(word_list, _HIGHER_TAXON_CS):
            return {'regex': _HIGHER_TAXON_CS, 'code': FragType.HIGHER_TAXON_CASE_S, 'num_groups':1}
    else:
        if _matches_all(word_list, _VAR):
            return {'regex': _VAR, 'code': FragType.VAR, 'num_groups':1}
        if _matches_all(word_list, _SP):
            return {'regex': _SP, 'code': FragType.SP, 'num_groups':1}
        if _matches_all(word_list, _SSP):
            return {'regex': _SSP, 'code': FragType.SSP, 'num_groups':1}
        if _matches_all(word_list, _CF):
            return {'regex': _CF, 'code': FragType.CF, 'num_groups':1}
        if _matches_all(word_list, _AFF):
            return {'regex': _AFF, 'code': FragType.AFF, 'num_groups':1}
    if _matches_all(word_list, _GENBANK):
        return {'regex': _GENBANK, 'code': FragType.CF, 'num_groups':1}
    if _matches_all(word_list, _TAXON_CI):
        return {'regex': _TAXON_CI, 'code': FragType.TAXON_CASE_I, 'num_groups':1}
    return None

_SPACE = re.compile(r'\s')
_WHITESPACE = re.compile(r'\s')
_PUNCTUATION_STR = r'[-~`<>._,;+?!@#$%^&()+={}|\\\[\]]'
_PUNCTUATION = re.compile( _PUNCTUATION_STR)
_NUMBER = re.compile(r'[0-9]')
_UC_LETTER = re.compile(r'[A-Z]')
_LC_LETTER = re.compile(r'[a-z]')

def _char_set2char_class(cs):
    if not isinstance(cs, set):
        cs = set(cs)
    if len(cs) == 1:
        c = list(cs)[0]
        if c == ' ':
            return dict(pat=' ', code=FragType.SPACE)
        if _WHITESPACE.match(c):
            return dict(pat=r'\s', code=FragType.WHITESPACE)
        if _PUNCTUATION.match(c):
            return dict(pat=_PUNCTUATION_STR, code=FragType.PUNCTUATION)
        if _NUMBER.match(c):
            return dict(pat=r'[0-9]', code=FragType.NUMBER)
        if _UC_LETTER.match(c):
            return dict(pat=r'[A-Z]', code=FragType.UC_LETTER)
        if _LC_LETTER.match(c):
            return dict(pat=r'[A-Z]', code=FragType.LC_LETTER)
        raise NotImplementedError('regex for "{}"'.format(c))

    if _matches_all(cs, _SPACE):
        return dict(pat=' ', code=FragType.SPACE)
    if _matches_all(cs, _WHITESPACE):
        return dict(pat=r'\s', code=FragType.WHITESPACE)
    if _matches_all(cs, _PUNCTUATION_STR):
        return dict(pat=_PUNCTUATION_STR, code=FragType.PUNCTUATION)
    if _matches_all(cs, _NUMBER):
        return dict(pat=r'[0-9]', code=FragType.NUMBER)
    if _matches_all(cs, _UC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.UC_LETTER)
    if _matches_all(cs, _LC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.LC_LETTER)
    return None


def _midwords2char_class(word_list, start_ind, end_ind):
    if not isinstance(cs, set):
        cs = set(cs)
    if len(cs) == 1:
        c = list(cs)[0]
        if c == ' ':
            return dict(pat=' ', code=FragType.SPACE)
        if _WHITESPACE.match(c):
            return dict(pat=r'\s', code=FragType.WHITESPACE)
        if _PUNCTUATION.match(c):
            return dict(pat=_PUNCTUATION_STR, code=FragType.PUNCTUATION)
        if _NUMBER.match(c):
            return dict(pat=r'[0-9]', code=FragType.NUMBER)
        if _UC_LETTER.match(c):
            return dict(pat=r'[A-Z]', code=FragType.UC_LETTER)
        if _LC_LETTER.match(c):
            return dict(pat=r'[A-Z]', code=FragType.LC_LETTER)
        raise NotImplementedError('regex for "{}"'.format(c))

    if _matches_all(cs, _SPACE):
        return dict(pat=' ', code=FragType.SPACE)
    if _matches_all(cs, _WHITESPACE):
        return dict(pat=r'\s', code=FragType.WHITESPACE)
    if _matches_all(cs, _PUNCTUATION_STR):
        return dict(pat=_PUNCTUATION_STR, code=FragType.PUNCTUATION)
    if _matches_all(cs, _NUMBER):
        return dict(pat=r'[0-9]', code=FragType.NUMBER)
    if _matches_all(cs, _UC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.UC_LETTER)
    if _matches_all(cs, _LC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.LC_LETTER)
    return None

def attempt_to_create_intervening_regex_from_words(preceding, word_list, following):
    if not isinstance(word_list, set):
        word_list = set(word_list)
    non_empty = []
    leading = set()
    trailing = set()
    has_empty = False
    for word in word_list:
        if not word:
            has_empty = True
        else:
            non_empty.append(word)
            leading.add(word[0])
            trailing.add(word[-1])

    if not has_empty and _matches_all(non_empty, _GENBANK):
        full_pat =  {'regex': _GENBANK, 'code': FragType.CF, 'num_groups':1}
    else:
        if preceding is None:
            if not non_empty:
                return {'regex': '^', 'num_groups':0, 'code': FragType.EMPTY}
            ws_ind = 0
            leading_pat = dict(pat='^', code=FragType.START)
        else:
            ws_ind = 1
            leading_pat = _char_set2char_class(leading)
            if leading_pat is None:
                return None
        if following is None:
            if not non_empty:
                return {'regex': '$', 'num_groups':0, 'code': FragType.EMPTY}
            trail_pat = dict(pat='$', code=FragType.END)
            we_ind = None
        else:
            we_ind = -1
            trail_pat = _char_set2char_class(trailing)
            if trail_pat is None:
                return None
        mid_pat = _midwords2char_class(non_empty, ws_ind, we_ind)
        if mid_pat is None:
            return None
        full_pat = (leading_pat, mid_pat, trail_pat)
    if not _can_transition(preceding, full_pat, following):
        return None
    if isinstance(full_pat, tuple):
        return _join_patterns(full_pat)
    return full_pat

def attempt_to_create_taxonomic_regex_from_lib(save_odd_el_list):
    '''Takes a list of lists of strings. The goal is to return a set of regex patterns
    that will match all elements (where the element is the ''.joined string)
    and have a group that will return the words in the odd numbered indices.
    
    assumes that all lists in save_odd_el_list are the same length
    returns None or a list of OTULabelStringCruncher objects.
    '''
    if not save_odd_el_list:
        return None
    nw = len(save_odd_el_list[0])
    assert (nw % 2) == 1
    str_collections = [list() for i in range(nw)]
    for el in save_odd_el_list:
        assert len(el) == nw
        for i, word in enumerate(el):
            str_collections[i].append(word)
    pat_list = [None for i in range(nw)]
    for i in range(1, nw - 1, 2):
        p = attempt_to_create_taxonomic_regex_from_words(str_collections[i])
        if p is None:
            return
        pat_list[i] = p
    for i in range(0, nw, 2):
        if i == 0:
            preceding = None
        else:
            preceding = pat_list[i - 1]
        if i == (nw - 1):
            following = None
        else:
            following = pat_list[i + 1]
        p = attempt_to_create_intervening_regex_from_words(preceding, str_collections[i], following)
        if p is None:
            return
        pat_list[i] = p
    return OTULabelStringCruncher(pat_list)


def build_taxonomic_regex(input_output_list):
    lib = create_library_of_intervening_fragments(input_output_list)
    regex_list = []
    for el in lib[-1::-1]:
        if not el:
            continue
        r = attempt_to_create_taxonomic_regex_from_lib(el)
        if r is not None:
            regex_list.append(r)
    if regex_list:
        return regex_list
    return None


def create_library_of_intervening_fragments(input_output_list):
    '''Takes a list of (input_str, output_str) tuples
    Each output_str is expeceted to be a whitespace-delimited series of words (like the names in OTT)

    returns a list. for each element in the list, there will be a series of lists
    representing the output of find_intervening_fragments for output_str of that # or words
    *with the expeceted words intercalated*

    For example 'Homo sapiens' is 2 words, so the the input element:
        ('blah Homo_sapiens+515', 'Homo sapiens')
    would result in a n entry in the returned list at index 2. The content contributed
    by this pair would be the list [['blah ', 'Homo', '_', 'sapiens', '+515']]
    because find_intervening_fragments will return [['blah ', '_', '+515']]

    This function assists in the creation of regex to match the expeceted patterns.
    '''
    library = [[]]
    for input_str, output_str in input_output_list:
        expected_str_list = output_str.split()
        le = len(expected_str_list)
        res = find_intervening_fragments(input_str, expected_str_list)
        if res is not None:
            while le >= len(library):
                library.append([])
            x = []
            for el in res:
                y = [el[0]]
                for i in range(1, len(el)):
                    y.append(expected_str_list[i - 1])
                    y.append(el[i])
                x.append(y)
            library[le].append(x)
    return library
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

