# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals

'''Timemap parser and access container.'''


import codecs
from datetime import datetime
import dateutil.parser
import dateutil.tz
import re
import urllib2
import urlparse


#==================================================================
class LinkTimemap(object):
#==================================================================

    #==========================================================================
    # Initialization and factory methods
    #==========================================================================

    def __init__(self, original_uri,
                 timegate_uri, timemap_uri, mementos=None,
                 from_datetime=None, until_datetime=None):
        """
        Initialize a new 'Link-Timemap'.  Use 'from_file' and 'from_uri'
        instead of this constructor.
        """
        self.original_uri = original_uri
        self.timegate_uri = timegate_uri
        self.timemap_uri = timemap_uri
        self.mementos = mementos
        self.from_datetime = from_datetime
        self.until_datetime = until_datetime
        self.assert_validity(include_mementos=(mementos is not None))


    @staticmethod
    def from_file(filename, base_uri, encoding='utf-8'):
        """
        Create a new LinkTimemap instance from the contents of a file.

        Parse the contents of 'filename' creating a 'LinkTimemap' representing
        the contents.  Resolve relative URIs using 'base_uri'.

        Args:
            filename: The name of the file containing the link timemap.
            base_uri: The URI from which the file was downloaded.

        Returns:
            A LinkTimemap.
        """
        with codecs.open(filename, 'r', encoding) as tmfile:
            parser = LinkTimemap._link_stream(tmfile)
            timemap = LinkTimemap._from_link_stream(parser, base_uri)
        return timemap


    @staticmethod
    def from_uri(uri_t):
        """
        Create a new LinkTimemap instance by dereferencing a URI-T.

        Parse the representation of 'uri_t' creating a 'LinkTimemap' from the
        the representation.  Resolve relative URIs using 'uri_t' as the base.

        Args:
            uri_t: The URI-T to be dereferenced.

        Returns:
            A LinkTimemap.
        """
        with urllib2.urlopen(uri_t) as tmfile:
            parser = LinkTimemap._link_stream(tmfile)
            timemap = LinkTimemap._from_link_stream(parser, uri_t)
        return timemap


    #==========================================================================
    # Act like a collection
    #==========================================================================

    def __getitem__(self, memento_datetime):
        """
        Return the set of URI-Ms for the specified Memento-Datetime.

        Args:
            memento_datetime: the Memento-Datetime of the memento(s) to be retrieved.

        Returns:
            A set of URI-Ms.

        Raises:
            KeyError: if no URI-Ms are available for the specified Memento-Datetime.
        """
        return self.mementos[memento_datetime]


    #==========================================================================
    # String representation
    #==========================================================================

    def __repr__(self):
        """
        Dump a 'LinkTimemap' is (somewhat) human-readable form.
        """
        return ''.join(['LinkTimemap<',
               'original: ', repr(self),
               ', timegate: ', repr(self.timegate),
               ', timemap: ', repr(self.timemap),
               ', mementos: ', repr(self.mementos),
               '>'])


    #==========================================================================
    # Parsing
    #==========================================================================

    TOKENIZER_RE = re.compile('(<[^>]+>|[a-zA-Z]+="[^"]*"|[;,])\\s*')
    URI_DATETIME_RE = re.compile('/([12][90][0-9][0-9][01][0-9][0123][0-9]'
                                 '[012][0-9][0-5][0-9][0-5][0-9])/',
                                 re.IGNORECASE)
    URI_DATETIME_FORMAT = '%Y%m%d%H%M%S'


    @staticmethod
    def _from_link_stream(link_stream, base_uri):
        """
        Create a 'LinkTimemap' from a timemap's list links.

        Args:
            link_stream: an iterable that provides a list of all the links
                in the timemap's representation.
            base_uri: The base URI used to resolve relative URIs.

        Returns:
            A 'LinkTimemap'.
        """
        original_uri = None
        timegate_uri = None
        timemap_uri = None
        from_datetime = None
        until_datetime = None
        mementos = dict()
        for link in link_stream:
            (rels, uri, memento_datetime, content_type) = link[:4]
            if 'memento' in rels:
                if memento_datetime not in mementos:
                    mementos[memento_datetime] = set()
                mementos[memento_datetime].add(urlparse.urljoin(base_uri, uri))
            elif 'original' in rels:
                original_uri = urlparse.urljoin(base_uri, uri)
            elif 'timegate' in rels:
                timegate_uri = urlparse.urljoin(base_uri, uri)
            elif 'timemap' in rels or 'self' in rels:
                timemap_uri = urlparse.urljoin(base_uri, uri)
                from_datetime, until_datetime = link[4:]

            # TODO: handle self timemap
            # TODO: handle list of timemaps

        timemap = LinkTimemap(original_uri, timegate_uri, timemap_uri, mementos,
                              from_datetime, until_datetime)
        return timemap


    @staticmethod
    def _link_stream(tmfile):
        """
        Parse a 'LinkTimemap'.
        """
        uri = None
        datetime = None
        from_datetime = None
        until_datetime = None
        rels = []
        content_type = None
        tokens = LinkTimemap._tokenizer(tmfile)
        for token in tokens:
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
                rels = token[5:-1].split()
            elif token[:5] == 'type=':
                content_type = token[6:-1]
            elif token == ';':
                pass
            elif token == ',':
                yield (rels, uri, LinkTimemap._currate_datetime(datetime, uri),
                       content_type,
                       LinkTimemap._currate_datetime(from_datetime),
                       LinkTimemap._currate_datetime(until_datetime))
            else:
                raise Exception('Unexpected timemap token', token)
        if uri is not None:
            yield (rels, uri, LinkTimemap._currate_datetime(datetime, uri),
                   content_type)
        tokens.close()


    @staticmethod
    def _tokenizer(timemap_file):
        """
        Generate a stream of tokens from a link timemap representation.  These
        tokens are consumed by '_link_stream'.
        """
        tmfile = timemap_file
        for line in tmfile:
            tokens = LinkTimemap.TOKENIZER_RE.findall(line)
            for token in tokens:
                yield token


    @staticmethod
    def _currate_datetime(dt, uri=None):
        if dt is None:
            return None
        if (dt.tzname() != 'UTC'):
            dt = dt.astimezone(dateutil.tz.tzutc())
        if uri is None:
            return dt
        # See if the time looks fishy (time == 00:00:00)
        if dt.hour != 0 or dt.minute != 0 or dt.second != 0:
            return dt
        # See if the uri has a YYYYMMDDHHMMSS dt in it, if so fix the time
        match = LinkTimemap.URI_DATETIME_RE.search(uri)
        if match is None:
            return dt
        # If the date is the same, replace the time with the URI time
        uri_datetime = dt.strptime(match.group(1), LinkTimemap.URI_DATETIME_FORMAT)
        if uri_datetime.year == dt.year \
               and uri_datetime.month == dt.month \
               and uri_datetime.day == dt.day:
            return dt.replace(hour = uri_datetime.hour,
                              minute = uri_datetime.minute,
                              second = uri_datetime.second)
        else:
            return dt


    #==========================================================================
    # Parsing
    #==========================================================================

    def assert_validity(self, include_mementos = False):
        """
        Timemaps are frequently not quite to specification, which makes parsing
        and analysing them a bit tricky.  This function checks for validity
        and is mostly a debugging aid.
        """
        if not __debug__:
            return
        assert not self.original_uri or isinstance(self.original_uri, unicode), repr(self.original_uri)
        assert not self.timegate_uri or isinstance(self.timegate_uri, unicode), repr(self.timegate_uri)
        assert not self.timemap_uri or isinstance(self.timemap_uri, unicode), repr(self.timemap_uri)
        if self.mementos is not None:
            assert isinstance(self.mementos, dict)
            for memento_datetime, uri_ms in self.mementos.iteritems():
                assert isinstance(memento_datetime, datetime), 'memento_datetime = {0!r}'.format(memento_datetime)
                assert isinstance(uri_ms, set), 'uri_ms = {0!r}'.format(uri_ms)
                for uri_m in uri_ms:
                    assert isinstance(uri_m, unicode), 'uri_m = {0!r}'.format(uri_m)
        assert not self.from_datetime or isinstance(self.from_datetime, datetime), repr(self.from_datetime)
        assert not self.until_datetime or isinstance(self.until_datetime, datetime), repr(self.until_datetime)


#end