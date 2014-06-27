# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals


import codecs
from datetime import datetime
import dateutil.parser
import dateutil.tz
import re
import StringIO
import urllib2
import urlparse


#==========================================================================
# Container classes for complex links
#==========================================================================

class MementoLink(object):
    """
    Container class for memento links.

    Attributes (from RFC 7089):
        datetime: a datetime with timezone set to GMT.
        uri_m: a unicode string representing the URI-M.
        rels: a list of unicode strings representing the link relations of this
              memento within a timemap.  Since every memento will have the
              memento link relation, the memento link relations should not be
              included.  If there are no link relations (other than memento),
              use None.
        license_uri: an optional unicode string containing the URI of a license.
                     If a license is not associated with this memento, use None.
    """
    def __init__(self, memento_datetime, uri_m, rels=None, license_uri=None):
        """
        Initialize a new MementoLink from a specified URI-M, list of link
        relations, and license URI.
        """
        super(MementoLink, self).__init__()
        self.memento_datetime = memento_datetime
        self.uri_m            = uri_m
        self.rels             = rels
        self.license_uri      = license_uri

    def __repr__(self):
        """
        Dump a 'MementoLink' in human-readable form.
        """
        return ''.join(['MementoLink<',
               'memento_datetime: ', repr(self.memento_datetime),
               ', uri_m: ', repr(self.uri_m),
               ', rels: ', repr(self.rels),
               ', license_uri: ', repr(self.license_uri),
               '>'])


class TimemapLink(object):
    """
    Container class for timemap links.

    Attributes (from RFC 7089):
        uri_t: a unicode string representing the URI-T.
        from_datetime: a datetime with timezone set to GMT (RFC 7089 'from').
        until_datetime: a datetime with timezone set to GMT (RFC 7089 'until').
        mime_type: a unicode string containing the media type (RFC 7089 'type').
    """
    def __init__(self, uri_t, from_dt, until_dt, mime_type):
        super(TimemapLink, self).__init__()
        self.uri_t     = uri_t
        self.from_dt   = from_dt
        self.until_dt  = until_dt
        self.mime_type = mime_type

    def __repr__(self):
        """
        Dump a 'TimemapLink' in human-readable form.
        """
        return ''.join(['TimemapLink<',
               'uri_t: ', repr(self.uri_t),
               ', from_dt: ', repr(self.from_dt),
               ', until_dt: ', repr(self.until_dt),
               ', mime_type: ', repr(self.mime_type),
               '>'])


class LinkTimemap(object):
    """
    Parser and container for RFC 7089 timemaps.

    Attributes (from RFC 7089):
        original_uri: a unicode string containing the original URI-R.
        timegate_uris: a list of unicode strings containing URI-Gs.
        timemaps: a list of TimemapLinks containing timemap link data.
                  (Note: timemaps[0] is the 'self' timemap link.)
        mementos: a list of MementoLinks containing memento link data.
    """

    #==========================================================================
    # Initialization and factory methods
    #==========================================================================

    def __init__(self, original_uri, timegate_uris, timemaps, mementos=None):
        """
        Initialize a new 'Link-Timemap'.  Use 'from_file' and 'from'
        instead of this constructor.

        Args:
            original_uri: a unicode string containing the original URI-R.
            timegate_uris: a list of unicode strings containing URI-Gs.
            timemaps: a list of TimemapLinks containing timemap link data.
                      (Note: timemaps[0] is the 'self' timemap link.)
            mementos: a list of MementoLinks containing memento link data.
        """
        self.original_uri  = original_uri
        self.timegate_uris = timegate_uris
        self.timemaps      = timemaps
        self.mementos      = mementos
        #self.assert_validity(include_mementos=(mementos is not None))


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
    def from_string(timemap_text, base_uri):
        """
        Create a new LinkTimemap instance from the contents of a string.

        Parse the contents of 'filename' creating a 'LinkTimemap' representing
        the contents.  Resolve relative URIs using 'base_uri'.

        Args:
            timemap_text: A string containing a complete link timemap.
            base_uri: The URI from which the file was downloaded.

        Returns:
            A LinkTimemap.
        """
        with StringIO.StringIO(timemap_text) as tmfile:
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
        # TODO: add "Accept: application/link-format;q=1.0" HTTP header
        with urllib2.urlopen(uri_t) as tmfile:
            parser = LinkTimemap._link_stream(tmfile)
            timemap = LinkTimemap._from_link_stream(parser, uri_t)
        return timemap


    def __getitem__(self, memento_datetime):
        """
        Return the set of URI-Ms for the specified MementoLink-Datetime.

        Args:
            memento_datetime: the MementoLink-Datetime of the memento(s) to be retrieved.

        Returns:
            A set of URI-Ms.

        Raises:
            KeyError: if no URI-Ms are available for the specified MementoLink-Datetime.
        """
        return self.mementos[memento_datetime]


    #==========================================================================
    # String representation
    #==========================================================================

    def __repr__(self):
        """
        Dump a 'LinkTimemap' in human-readable form.
        """
        return ''.join(['LinkTimemap<',
               'original_uri: ', repr(self.original_uri),
               ', timegate_uris: ', repr(self.timegate_uris),
               ', timemaps: ', repr(self.timemaps),
               ', mementos: ', repr(self.mementos),
               '>'])


    #==========================================================================
    # Parser
    #==========================================================================

    # TODO: Move parser to separate class

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
        original_uri = None   # The original IRI-R
        timegates    = []     # List of timegate linkss in this timemap
        timemaps     = []     # List of timemap links in this timemap
        mementos     = dict() # List of mement links in this timemap
        for link in link_stream:
            (rels, uri, memento_datetime, mime_type, license) = link[:5]
            if 'memento' in rels:
                if memento_datetime not in mementos:
                    mementos[memento_datetime] = set()
                uri_m = urlparse.urljoin(base_uri, uri)
                mementos[memento_datetime].add(
                        MementoLink(uri_m, rels, license))
            elif 'original' in rels:
                original_uri = urlparse.urljoin(base_uri, uri)
            elif 'timegate' in rels:
                uri_g = urlparse.urljoin(base_uri, uri)
                timegates.append(uri_g)
            elif 'timemap' in rels or 'self' in rels:
                uri_t = urlparse.urljoin(base_uri, uri)
                from_dt, until_dt = link[5:]
                timemap_link = TimemapLink(uri_t, from_dt, until_dt, mime_type)
                if 'self' in rels:
                    timemaps.insert(0, timemap_link)
                else:
                    timemaps.append(timemap_link)
        timemap = LinkTimemap(original_uri, timegates, timemaps, mementos)
        return timemap


    @staticmethod
    def _link_stream(tmfile):
        """
        Parse a 'LinkTimemap'.
        """
        uri       = None
        rels      = []
        datetime  = None
        from_dt   = None
        until_dt  = None
        mime_type = None
        license   = None
        tokens    = LinkTimemap._tokenizer(tmfile)
        for token in tokens:
            if token[0] == '<':
                uri = token[1:-1]
            elif token[:9] == 'datetime=':
                raw_dt = token[10:-1]
                datetime = dateutil.parser.parse(raw_dt)
            elif token[:5] == 'from=':
                raw_dt = token[6:-1]
                from_dt = dateutil.parser.parse(raw_dt)
            elif token[:6] == 'until=':
                raw_dt = token[7:-1]
                until_dt = dateutil.parser.parse(raw_dt)
            elif token[:4] == 'rel=':
                rels = token[5:-1].split()
            elif token[:5] == 'type=':
                mime_type = token[6:-1]
            elif token[:7] == 'license=':
                mime_type = token[8:-1]
            elif token == ';':
                pass
            elif token == ',':
                yield (rels, uri, LinkTimemap._currate_datetime(datetime, uri),
                       mime_type, license,
                       LinkTimemap._currate_datetime(from_dt),
                       LinkTimemap._currate_datetime(until_dt))
            else:
                raise Exception('Unexpected timemap token', token)
        if uri is not None:
            yield (rels, uri, LinkTimemap._currate_datetime(datetime, uri),
                   mime_type, license)
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
    # Check for validity -- debugging aid
    #==========================================================================

    def assert_validity(self, include_mementos = False):
        """
        Timemaps are frequently not quite to specification, which makes parsing
        and analysing them a bit tricky.  This function checks for validity
        and is mostly a debugging aid.
        """
        # TODO: Update this to match RFC 7089
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
