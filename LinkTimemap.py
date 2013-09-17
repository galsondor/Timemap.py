# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals

'''Timemap parser and access container.'''
__author__ = 'Scott G. Ainsworth'
__id__ = '$Id: timemaps.py 493 2013-01-09 20:51:47Z sainswor $'

import dateutil.parser
import re
import urllib2

from data import utc
from net import URI


#==================================================================
# REGULAR EXPRESSIONS
#==================================================================

TOKENIZER_RE = re.compile('(<[^>]+>|[a-zA-Z]+="[^"]*"|[;,])\\s*')
URI_DATETIME_RE = re.compile('/([12][90][0-9][0-9][01][0-9][0123][0-9]'
                             '[012][0-9][0-5][0-9][0-5][0-9])/',
                             re.IGNORECASE)
URI_DATETIME_FORMAT = '%Y%m%d%H%M%S'


#==================================================================
class LinkTimemap(object):
#==================================================================

    @classmethod
    def from_file(cls, filename, base_uri):
        with open(filename, 'r') as tmfile:
            parser = _LinkTimeMapParser(tmfile)
            timemap = LinkTimemap.from_parser(parser, base_uri)
        return timemap

    @classmethod
    def from_uri(cls, uri, base_uri):
        with urllib2.urlopen(uri) as tmfile:
            parser = _LinkTimeMapParser(tmfile)
            timemap = LinkTimemap.from_parser(parser, base_uri)
        return timemap

    def __init__(self, original_uri,
                 timegate_uri, timemap_uri, mementos=None,
                 from_datetime=None, until_datetime=None):
        self.original_uri = original_uri
        self.timegate_uri = timegate_uri
        self.timemap_uri = timemap_uri
        self.mementos = mementos
        self.from_datetime = from_datetime
        self.until_datetime = until_datetime
        self.assert_validity(include_mementos=(mementos is not None))

    @staticmethod
    def from_parser(parser, base_uri):
        original_uri = None
        timegate_uri = None
        timemap_uri = None
        from_datetime = None
        until_datetime = None
        mementos = dict()
        for link in parser:
            rels = link[0].split()
            if 'memento' in rels:
                if link[1] not in mementos:
                    mementos[link[1]] = set()
                mementos[link[1]].add(URI(link[2], base_uri))
            elif 'original' in rels:
                original_uri = URI(link[2], base_uri)
            elif 'timegate' in rels:
                timegate_uri = URI(link[2], base_uri)
            elif 'timemap' in rels or 'self' in rels:
                timemap_uri = URI(link[2], base_uri)
                from_datetime = link[4]
                until_datetime = link[5]
        timemap = LinkTimemap(original_uri, timegate_uri, timemap_uri, mementos,
                              from_datetime, until_datetime)
        return timemap
    
    def assert_validity(self, include_mementos = False):
        if not __debug__:
            return
        assert not self.original_uri or isinstance(self.original_uri, URI), repr(self.original_uri)
        assert not self.timegate_uri or isinstance(self.timegate_uri, URI), repr(self.timegate_uri)
        assert not self.timemap_uri or isinstance(self.timemap_uri, URI), repr(self.timemap_uri)
        if self.mementos is not None:
            assert isinstance(self.mementos, dict)
            for memento_datetime, uri_ms in self.mementos.iteritems():
                assert isinstance(memento_datetime, utc.datetime), 'memento_datetime = {0!r}'.format(memento_datetime)
                assert isinstance(uri_ms, set), 'uri_ms = {0!r}'.format(uri_ms)
                for uri_m in uri_ms:
                    assert isinstance(uri_m, URI), 'uri_m = {0!r}'.format(uri_m)
        assert not self.from_datetime or isinstance(self.from_datetime, utc.datetime), repr(self.from_datetime)
        assert not self.until_datetime or isinstance(self.until_datetime, utc.datetime), repr(self.until_datetime)

    def __getitem__(self, memento_datetime):
        return self.mementos[memento_datetime]

    def __repr__(self):
        return ''.join(['LinkTimemap<',
               'original: ', repr(self),
               ', timegate: ', repr(self.timegate),
               ', timemap: ', repr(self.timemap),
               ', mementos: ', repr(self.mementos),
               '>'])

#==================================================================
class _LinkTimeMapParser(object):
#==================================================================

    def __init__(self, tmfile):
        self.tokens = _TimeMapTokenizer(tmfile)

    def __iter__(self):
        return self

    def next(self):
        uri = None
        datetime = None
        from_datetime = None
        until_datetime = None
        rel = None
        resource_type = None
        for token in self.tokens:
            if token[0] == '<':
                uri = token[1:-1]
            elif token[:9] == 'datetime=':
                raw_datetime = token[10:-1]
                datetime = dateutil.parser.parse(raw_datetime)
            elif token[:5] == 'from=':
                raw_datetime = token[6:-1]
                from_datetime = dateutil.parser.parse(raw_datetime)
            elif token[:6] == 'until=':
                raw_datetime = token[7:-1]
                until_datetime = dateutil.parser.parse(raw_datetime)
            elif token[:4] == 'rel=':
                rel = token[5:-1]
            elif token[:5] == 'type=':
                resource_type = token[6:-1]
            elif token == ';':
                pass
            elif token == ',':
                return (rel, self.currate_datetime(datetime, uri),
                        uri, resource_type, from_datetime, until_datetime)
            else:
                raise Exception('Unexpected timemap token', token)
        if uri is None:
            self.tokens.close()
            raise StopIteration
        else:
            return (rel, self.currate_datetime(datetime, uri), uri, resource_type)

    def currate_datetime(self, datetime, uri):
        if uri is None:
            return datetime
        if datetime is None:
            return None
        # See if the time looks fishy (i.e. == 00:00:00)
        # -- negative logic
        if datetime.hour != 0 or datetime.minute != 0 or datetime.second != 0:
            return datetime
        # See if the uri has a YYYYMMDDHHMMSS datetime in it
        # -- negative logic
        match = URI_DATETIME_RE.search(uri)
        if match is None:
            return datetime
        # If the date is the same, replace the time with the URI time
        uri_datetime = datetime.strptime(match.group(1), URI_DATETIME_FORMAT)
        if uri_datetime.year == datetime.year \
               and uri_datetime.month == datetime.month \
               and uri_datetime.day == datetime.day:
            return datetime.replace(hour = uri_datetime.hour,
                                    minute = uri_datetime.minute,
                                    second = uri_datetime.second)
        else:
            return datetime

#==================================================================
class _TimeMapTokenizer(object):
#==================================================================

    def __init__(self, timemap_file):
        self._tmfile = timemap_file
        self._tokens = []

    def __del__(self):
        self.close()

    def close(self):
        if self._tmfile is not None:
            self._tmfile.close()
            self._tmfile = None

    def __iter__(self):
        return self

    def next(self):
        if len(self._tokens) == 0:
            line = self._tmfile.readline()
            if len(line) == 0:
                raise StopIteration
            self._tokens = TOKENIZER_RE.findall(line)
        return self._tokens.pop(0)

#end

