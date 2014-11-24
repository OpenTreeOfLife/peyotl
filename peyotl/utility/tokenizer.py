#!/usr/bin/env python
from peyotl.utility import get_logger
from enum import Enum
import re
_LOG = get_logger(__name__)
_WS = re.compile(r'\s+')
_PUNC = re.compile(r'[(),:;\[\]]')
_SINGLE_QUOTED_STR = re.compile(r"([^']*)'")
_COMMENT_STR = re.compile(r"([^\]]*)\]")
_UNQUOTED_STR = re.compile(r"([^'():,;\\[]+)(?=$|['():,;\\[])")
class NewickTokenType(Enum):
    NONE = 0
    OPEN = 1
    CLOSE = 2
    COMMA = 3
    COLON = 4
    LABEL = 5
    EDGE_INFO = 6
    SEMICOLON = 7

class NewickTokenizer(object):
    '''given a file-like object, this becomes an iterator
    over the newick tokens in the file-object.
    Name tokens are stripped of whitespace and comments.
    '''
    def __init__(self, stream):
        self._src = stream.read()
        self._last_ind = len(self._src) - 1
        self._index = -1
        self.num_open_parens = 0
        self.num_close_parens = 0
        self._token = None
        self.comments = []
        self.prev_token = NewickTokenType.NONE
        self._cb = {'(': self._handle_open_parens,
                    ')': self._handle_close_parens,
                    ',': self._handle_comma,
                    ':': self._handle_colon,
                    ';': self._handle_semicolon,
                    '[': self._handle_comment,
                   }
        self._default_cb = self._handle_label
        self.finished = False
        c = self._eat_whitespace_get_next_char()
        self._index -= 1
        if c != '(':
            self._raise_unexpected('Expected the first character to be a "(", but found "{}"'.format(c))
        self.prev_token = NewickTokenType.OPEN # just so we don't have to check for NONE on every ( we fake a legal preceding token
    def tokens(self):
        return [i for i in iter(self)]
    def _raise_unexpected(self, m):
        if self.prev_token != NewickTokenType.NONE:
            raise ValueError('Error: {m} at {f} after a/an {p} token'.format(m=m, f=self.file_pos(), p=self.prev_token.name))
        raise ValueError('Error: {m} at {f}'.format(m=m, f=self.file_pos()))

    def __iter__(self):
        return self
    def _eat_whitespace(self):
        #if (1 + self._index) <= self._last_ind:
            #_LOG.debug('_eat_whitespace ind= {} str="{}"'.format(self._index, self._src[1+self._index]))
        w = _WS.match(self._src, 1 + self._index)
        if w:
            #_LOG.debug('found ws ending at {}'.format(w.end()))
            self._index = w.end() - 1
            #_LOG.debug('exiting _eat_whitespace ind= {} str="{}"'.format(self._index, self._src[1+self._index]))
    def _eat_whitespace_get_next_char(self):
        self._eat_whitespace()
        return self._get_next_char()
    def _get_next_char(self):
        self._index += 1
        try:
            x = self._src[self._index]
            if self.finished:
                raise ValueError('Unexpected newick content after the semicolon. Found "{c}" and {f}'.format(c=x, f=self.file_pos()))
            return x
        except IndexError:
            if self.num_close_parens != self.num_open_parens:
                raise ValueError('Number of close parentheses ({c:d}) does not equal '\
                                 'the number of open parentheses ({o:d}) at the end '\
                                 'of the input ({f:d}).'.format(c=self.num_close_parens,
                                                                o=self.num_open_parens,
                                                                f=self.file_pos()))
            raise StopIteration
    def _peek(self):
        if self._index >= self._last_ind:
            return None
        return self._src[1 + self._index]
    def _grab_one_single_quoted_word(self):
        b = self._index + 1
        m = _SINGLE_QUOTED_STR.match(self._src, b)
        #_LOG.debug('_grab_one_single_quoted_word b = {} str="{}"'.format(b, self._src[b:]))
        if not m:
            self._index = b - 1
            self._raise_unexpected("Found an opening single-quote, but not closing quote")
        self._index = m.end() - 1
        word = m.group(1)
        #_LOG.debug('  _grab_one_single_quoted_word word = {} index="{}"'.format(word, self._index))
        return word
    def _read_quoted_label(self):
        label = self._grab_one_single_quoted_word()
        if self._peek() == "'":
            word_list = [label]
            while self._peek() == "'":
                assert self._get_next_char() == "'"
                label = self._grab_one_single_quoted_word()
                word_list.append(label)
            return "'".join(word_list)
        return label
    def _read_unquoted_label(self):
        b = self._index
        #_LOG.debug('_read_unquoted_label b = {} str="{}"'.format(b, self._src[b:]))
        m = _UNQUOTED_STR.match(self._src, b) # called after we grabbed the first letter, so we look one back
        if not m:
            self._raise_unexpected('Expecting a label but found "{}"'.format(self._src[b]))
        label = m.group(1)
        self._index = m.end() - 1
        #_LOG.debug('_read_unquoted_label label = "{}" ind = {}'.format(label, self._index))
        label = label.strip() # don't preserve whitespace
        return label.replace('_', ' ')

    def _handle_open_parens(self):
        if self.prev_token != NewickTokenType.OPEN and self.prev_token != NewickTokenType.COMMA:
            self._raise_unexpected('Expecting "(" to be preceded by "," or "("')
        self.num_open_parens += 1
        self.prev_token = NewickTokenType.OPEN
        return '('
    def _handle_colon(self):
        if self.prev_token not in [NewickTokenType.LABEL, NewickTokenType.CLOSE]:
            self._raise_unexpected('Expecting ":" to be preceded by ")" or a taxon label')
        self.prev_token = NewickTokenType.COLON
        self._default_cb = self._handle_edge_info
        return ':'
    def _handle_comment(self):
        b = self._index + 1
        #_LOG.debug('_handle_comment b = {} str="{}"'.format(b, self._src[b:]))
        m = _COMMENT_STR.match(self._src, b)
        if not m:
            self._index = b
            self._raise_unexpected("Found an opening [ of a comment, but not closing ]")
        self._index = m.end() - 1
        comment = m.group(1)
        #_LOG.debug('_handle_comment = "{}" ind = {}'.format(comment, self._index))
        self.comments.append(comment)
        return self._read_next()
    def _handle_semicolon(self):
        if self.prev_token not in [NewickTokenType.LABEL, NewickTokenType.CLOSE, NewickTokenType.EDGE_INFO]:
            self._raise_unexpected('Expecting ";" to be preceded by ")", a taxon label, or branch information')
        self.finished = True
        self.prev_token = NewickTokenType.SEMICOLON
        return ';'
    def _handle_comma(self):
        if self.prev_token not in [NewickTokenType.LABEL, NewickTokenType.CLOSE, NewickTokenType.EDGE_INFO]:
            self._raise_unexpected('Expecting "," to be preceded by ")", a taxon label, or branch information')
        self.prev_token = NewickTokenType.COMMA
        return ','
    def file_pos(self):
        return 'character #{}'.format(1 + self._index)
    def _handle_edge_info(self):
        x = self._src[self._index]
        if x == "'":
            label = self._read_quoted_label()
        else:
            label = self._read_unquoted_label()
        assert self.prev_token == NewickTokenType.COLON
        self.prev_token = NewickTokenType.EDGE_INFO
        self._default_cb = self._handle_label
        return label
    def _handle_label(self):
        x = self._src[self._index]
        if x == "'":
            label = self._read_quoted_label()
        else:
            label = self._read_unquoted_label()
        if self.prev_token not in [NewickTokenType.OPEN, NewickTokenType.CLOSE, NewickTokenType.COMMA]:
            m = 'Found "{}", but expected a label to be preceded by "(", ")", or a comma'.format(label)
            self._raise_unexpected(m)
        self.prev_token = NewickTokenType.LABEL
        return label
    def _handle_close_parens(self):
        if self.prev_token != NewickTokenType.LABEL and self.prev_token != NewickTokenType.EDGE_INFO:
            self._raise_unexpected('Expecting ")" to be preceded by a label or branch information')
        self.num_close_parens += 1
        if self.num_close_parens > self.num_open_parens:
            self._raise_unexpected('Number of close parentheses exceeds the number of open parentheses')
        self.prev_token = NewickTokenType.CLOSE
        return ')'
    def __next__(self):
        del self.comments[:]
        c = self._read_next()
        #_LOG.debug('TOKEN = "{}" type={} ind={} comments="{}"'.format(c, self.prev_token, self._index, '", "'.join(self.comments)))
        return c
    def _read_next(self):
        c = self._eat_whitespace_get_next_char()
        #_LOG.debug('__next__ c = "{c}" prev_token={p} self._index={i}'.format(c=c, p=self.prev_token.name, i=self._index))
        cb = self._cb.get(c, self._default_cb)
        return cb()
    next = __next__

class NewickEvents(Enum):
    OPEN_SUBTREE = 0
    TIP = 1
    CLOSE_SUBTREE = 2
class NewickEventFactory(object):
    '''Higher level interface for reading newick strings.
    Provides either an iterator over OPEN_SUBTREE, TIP, and CLOSE_SUBTREE
    events in teh NewickEvents Enum, or calls a supplied event_handler for each event in the parsing.

    Each event will be a dict with the keys:
        'type': facet of the NewickEvents Enum, and
        'comments' a list of all comments contained
    TIP and CLOSE_SUBTREE events can also have a label or edge_info strings.
    *NOTE* for the sake of performance, the value of the comments field may be the same list!
    You must make a copy of it if you want to process comments later.
    '''
    def __init__(self, tokenizer=None, newick=None, event_handler=None):
        if tokenizer is None:
            if newick is None:
                raise ValueError('tokenizer or newick argument must be supplied')
            self._tokenizer = NewickTokenizer(newick)
        else:
            self._tokenizer = tokenizer
        self._base_it = iter(tokenizer)
        self._tok_stack = []
        self._start_pos = 0
        self._comments = []
        self._comments_stack = []
        self._prev_type = NewickEvents.OPEN_SUBTREE
        if event_handler is not None:
            for event in iter(self):
                event_handler(event)

    def __iter__(self):
        return self
    def __next__(self):
        del self._comments[:]
        if self._tok_stack:
            tok = self._tok_stack.pop()
            self._comments.extend(self._comments_stack)
            del self._comments_stack[:]
            assert not self._tok_stack
        else:
            tok = next(self._base_it)
            self._comments.extend(self._tokenizer.comments)
        if self._tokenizer.prev_token == NewickTokenType.OPEN:
            self._prev_type = NewickEvents.OPEN_SUBTREE
            return {'type': NewickEvents.OPEN_SUBTREE,
                    'comments': self._comments}
        elif self._tokenizer.prev_token == NewickTokenType.LABEL:
            # when reading a tip, be greedy about grabbing surrounding comments
            return self._greedy_token_seq(tok, NewickEvents.TIP)
        elif self._tokenizer.prev_token == NewickTokenType.CLOSE:
            # when reading a tip, be greedy about grabbing trailing comments
            return self._greedy_token_seq(tok, NewickEvents.CLOSE_SUBTREE)
        elif self._tokenizer.prev_token == NewickTokenType.COMMA:
            self._comments.extend(self._tokenizer.comments)
            return next(self)
        elif self._tokenizer.prev_token == NewickTokenType.SEMICOLON:
            raise StopIteration
        assert False
    def _greedy_token_seq(self, label, t):
        tok = next(self._base_it)
        self._comments.extend(self._tokenizer.comments)
        if t == NewickEvents.CLOSE_SUBTREE and self._tokenizer.prev_token == NewickTokenType.LABEL:
            label = tok
            tok = next(self._base_it)
            self._comments.extend(self._tokenizer.comments)

        if tok == ':':
            tok = next(self._base_it)
            self._comments.extend(self._tokenizer.comments)
            assert self._prev_type == NewickTokenType.EDGE_INFO
            edge_info = tok
            tok = next(self._base_it)
            self._comments.extend(self._tokenizer.comments)
        else:
            edge_info = None
        self._tok_stack.append(tok)
        self._prev_type = t
        return {'type': t,
                'label': label,
                'edge_info': edge_info,
                'comments': self._comments}
    next = __next__
