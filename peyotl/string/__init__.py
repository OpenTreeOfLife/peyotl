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

_ANY_FRAG = frozenset([FragType.EMPTY, FragType.SPACE, FragType.WHITESPACE, FragType.PUNCTUATION, FragType.NUMBER, FragType.UC_LETTER, FragType.LC_LETTER, FragType.START, FragType.END])
_NONLETTERS = frozenset([FragType.EMPTY, FragType.SPACE, FragType.WHITESPACE, FragType.PUNCTUATION, FragType.NUMBER, FragType.START, FragType.END])
_NON_UC_LETTERS = frozenset([FragType.EMPTY, FragType.SPACE, FragType.WHITESPACE, FragType.PUNCTUATION, FragType.NUMBER,  FragType.LC_LETTER, FragType.START, FragType.END])
_NON_LC_LETTERS = frozenset([FragType.EMPTY, FragType.SPACE, FragType.WHITESPACE, FragType.PUNCTUATION, FragType.NUMBER,  FragType.UC_LETTER, FragType.START, FragType.END])
_NON_NUMBERS = frozenset([FragType.EMPTY, FragType.SPACE, FragType.WHITESPACE, FragType.PUNCTUATION, FragType.UC_LETTER, FragType.LC_LETTER, FragType.START, FragType.END])
_CAN_FOLLOW = {
    FragType.HIGHER_TAXON_CASE_S: _NON_LC_LETTERS,
    FragType.TAXON_CASE_I: _NONLETTERS,
    FragType.EPITHET_CASE_S: _NON_LC_LETTERS,
    FragType.GENBANK_ACCESSION: _NON_NUMBERS,
    FragType.VAR: _NONLETTERS,
    FragType.SP: _NONLETTERS,
    FragType.SSP: _NONLETTERS,
    FragType.CF: _NONLETTERS,
    FragType.AFF: _NONLETTERS,
}
_CAN_PRECEED = {
    FragType.HIGHER_TAXON_CASE_S: frozenset(list(_NON_UC_LETTERS)+ [FragType.HIGHER_TAXON_CASE_S, FragType.EPITHET_CASE_S, FragType.GENBANK_ACCESSION ,
]),
    FragType.TAXON_CASE_I: _NONLETTERS,
    FragType.EPITHET_CASE_S: _NON_LC_LETTERS,
    FragType.GENBANK_ACCESSION: frozenset(list(_NON_UC_LETTERS) + [FragType.HIGHER_TAXON_CASE_S, FragType.EPITHET_CASE_S, FragType.GENBANK_ACCESSION ,
]),
    FragType.VAR: _NONLETTERS,
    FragType.SP: _NONLETTERS,
    FragType.SSP: _NONLETTERS,
    FragType.CF: _NONLETTERS,
    FragType.AFF: _NONLETTERS,
}

_HIGHER_TAXON_CS = re.compile(r'([-A-Z][a-z]{2,})')
_TAXON_CI = re.compile(r'([-A-Za-z]{3,})')
_EPITHET_CS = re.compile(r'([-a-z]{3,})')
_GENBANK = re.compile(r'([A-Z]{1,2}[0-9]{5,6})')
_VAR = re.compile(r'([vV][aA][rR]\.?)')
_SP = re.compile(r'([sS][pP]\.?)')
_SSP = re.compile(r'([sS][sS][pP]\.?)')
_CF = re.compile(r'([cC][fF]\.?)')
_AFF = re.compile(r'([aA][fF][fF]\.?)')


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
            return dict(pat=' ', code=FragType.SPACE, num_groups=0)
        if _WHITESPACE.match(c):
            return dict(pat=r'\s', code=FragType.WHITESPACE, num_groups=0)
        if _PUNCTUATION.match(c):
            return dict(pat=_PUNCTUATION_STR, code=FragType.PUNCTUATION, num_groups=0)
        if _NUMBER.match(c):
            return dict(pat=r'[0-9]', code=FragType.NUMBER, num_groups=0)
        if _UC_LETTER.match(c):
            return dict(pat=r'[A-Z]', code=FragType.UC_LETTER, num_groups=0)
        if _LC_LETTER.match(c):
            return dict(pat=r'[A-Z]', code=FragType.LC_LETTER, num_groups=0)
        raise NotImplementedError('regex for "{}"'.format(c))

    if _matches_all(cs, _SPACE):
        return dict(pat=' ', code=FragType.SPACE, num_groups=0)
    if _matches_all(cs, _WHITESPACE):
        return dict(pat=r'\s', code=FragType.WHITESPACE, num_groups=0)
    if _matches_all(cs, _PUNCTUATION):
        return dict(pat=_PUNCTUATION_STR, code=FragType.PUNCTUATION, num_groups=0)
    if _matches_all(cs, _NUMBER):
        return dict(pat=r'[0-9]', code=FragType.NUMBER, num_groups=0)
    if _matches_all(cs, _UC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.UC_LETTER, num_groups=0)
    if _matches_all(cs, _LC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.LC_LETTER, num_groups=0)
    return None

def _can_transition_preceding(preceding, full_pat):
    pc = preceding['code']
    fc = full_pat['code']
    return fc in _CAN_FOLLOW[pc]

def _can_transition_following(full_pat, following):
    pc = full_pat['code']
    fc = following['code']
    return pc in _CAN_PRECEED[fc]

def _can_transition(preceding, full_pat, following, has_empty):
    if isinstance(full_pat, tuple) or isinstance(full_pat, list):
        pa =  full_pat[0]
        fa =  full_pat[-1]
    else:
        pa, fa, = full_pat, full_pat
    if preceding is not None:
        if not _can_transition_preceding(preceding, pa):
            return False
    if following is not None:
        if not _can_transition_following(fa, following):
            return False
    if has_empty and (preceding is not None) and (following is not None):
        if not _can_transition_following(preceding, following):
            return False

    return True
def _midwords2char_class(word_list, start_ind, end_ind):
    if start_ind > 0 or (end_ind is not None):
        if end_ind is not None:
            word_list = [i[start_ind:end_ind] for i in word_list]
        else:
            word_list = [i[start_ind:] for i in word_list]
    if not isinstance(word_list, set):
        word_list = set(word_list)
    minl, maxl = None, None
    for word in word_list:
        if minl is None:
            minl = len(word)
        if maxl is None:
            maxl = len(word)
        minl = min(minl, len(word))
        maxl = max(maxl, len(word))
    if _matches_all(word_list, _SPACE):
        return dict(pat=' ', code=FragType.SPACE, minl=minl, maxl=maxl, num_groups=0)
    if _matches_all(word_list, _WHITESPACE):
        return dict(pat=r'\s', code=FragType.WHITESPACE, minl=minl, maxl=maxl, num_groups=0)
    if _matches_all(word_list, _PUNCTUATION):
        return dict(pat=_PUNCTUATION_STR, code=FragType.PUNCTUATION, minl=minl, maxl=maxl, num_groups=0)
    if _matches_all(word_list, _NUMBER):
        return dict(pat=r'[0-9]', code=FragType.NUMBER, minl=minl, maxl=maxl, num_groups=0)
    if _matches_all(word_list, _UC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.UC_LETTER, minl=minl, maxl=maxl, num_groups=0)
    if _matches_all(word_list, _LC_LETTER):
        return dict(pat=r'[A-Z]', code=FragType.LC_LETTER, minl=minl, maxl=maxl, num_groups=0)
    return None

def attempt_to_create_intervening_regex_from_words(preceding, word_list, following):
    if not isinstance(word_list, set):
        print 'word_list = ', word_list
        word_list = set(word_list)
    non_empty = []
    leading = set()
    trailing = set()
    has_empty = False
    maxl, minl = None, None
    for word in word_list:
        if not word:
            has_empty = True
            minl = 0
        else:
            if minl is None:
                maxl = len(word)
            else:
                minl = min(minl, len(word))
            if maxl is None:
                maxl = len(word)
            else:
                maxl = max(maxl, len(word))
            non_empty.append(word)
            leading.add(word[0])
            trailing.add(word[-1])

    if not has_empty and _matches_all(non_empty, _GENBANK):
        full_pat =  {'pat': _GENBANK, 'code': FragType.CF, 'num_groups':1}
    else:
        if minl == maxl and minl == 1:
            full_pat = _char_set2char_class(leading)
            if full_pat is None:
                _LOG.debug('could not find a single letter pattern')
                return None
        else:
            if preceding is None:
                if not non_empty:
                    return {'pat': '^', 'num_groups':0, 'code': FragType.EMPTY}
                ws_ind = 0
                leading_pat = dict(pat='^', code=FragType.START, num_groups=0)
            else:
                ws_ind = 1
                leading_pat = _char_set2char_class(leading)
                if leading_pat is None:
                    _LOG.debug('could not find a leading pattern')
                    return None
            if following is None:
                if not non_empty:
                    return {'pat': '$', 'num_groups':0, 'code': FragType.EMPTY}
                trail_pat = dict(pat='$', code=FragType.END, num_groups=0)
                we_ind = None
            else:
                we_ind = -1
                trail_pat = _char_set2char_class(trailing)
                if trail_pat is None:
                    _LOG.debug('could not find a trailing pattern')
                    return None
            mid_pat = _midwords2char_class(non_empty, ws_ind, we_ind)
            if mid_pat is None:
                return None
            full_pat = (leading_pat, mid_pat, trail_pat)
    if not _can_transition(preceding, full_pat, following, has_empty):
        return None
    if isinstance(full_pat, tuple):
        return _join_patterns(full_pat)
    return full_pat

def _join_patterns(pt):
    assert len(pt) == 3
    p = '{f}{s}{t}'.format(f=pt[0]['pat'],s=pt[1]['pat'],t=pt[2]['pat'])
    ng = pt[0]['num_groups'] + pt[1]['num_groups'] + pt[2]['num_groups'] 
    return dict(pat=p, num_groups=ng, minl=pt[1]['minl'], maxl=pt[1]['maxl'])

def attempt_to_create_taxonomic_regex_from_lib(save_odd_el_list):
    '''Takes a list of lists of strings. The goal is to return a set of regex patterns
    that will match all elements (where the element is the ''.joined string)
    and have a group that will return the words in the odd numbered indices.
    
    assumes that all lists in save_odd_el_list are the same length
    returns None or a list of OTULabelStringCruncher objects.
    '''
    if not save_odd_el_list:
        return None
    nw = len(save_odd_el_list[0][0])
    assert (nw % 2) == 1
    str_collections = [list() for i in range(nw)]
    _LOG.debug('save_odd_el_list = {}'.format(str(save_odd_el_list)))
    for el in save_odd_el_list:
        for i in range(1): #TODO should look at more than the first...
            assert len(el[i]) == nw
            for i, word in enumerate(el[i]): 
                str_collections[i].append(word)
    _LOG.debug('str_collections = {}'.format(str(str_collections)))
    pat_list = [None for i in range(nw)]
    for i in range(1, nw - 1, 2):
        is_first = i == 1
        p = attempt_to_create_taxonomic_regex_from_words(str_collections[i], is_first=is_first)
        _LOG.debug('pat_list[{i}] = {p}'.format(i=i, p=p))
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
        _LOG.debug('pat_list[{i}] = {p} from ({s})'.format(i=i, p=p, s=str(str_collections[i])))
        if p is None:
            return
        pat_list[i] = p
    _LOG.debug('pat_list = ' + str(pat_list))
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

