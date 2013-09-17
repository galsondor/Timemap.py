# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals

'''URI.'''
__author__ = 'Scott G. Ainsworth'
__id__ = '$Id$'

#import binascii
#import codecs
import hashlib
import re
import urllib
import urlparse
#import warnings

class URI(unicode):

    IPADDR_RE = re.compile('^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$')

    def __new__(cls, raw_uri, base_uri=None):
        if isinstance(raw_uri, URI):
            return raw_uri
        joined_uri = (raw_uri
                         if base_uri is None else
                      urlparse.urljoin(base_uri, raw_uri, True))
        uri, split  = URI.decode(joined_uri)
        self = super(URI, cls).__new__(cls, uri)
        self.split = split
        self.hash = URI.make_hash(uri)
        return self

    def __call__(self, raw_uri):
        return URI(raw_uri)

    @staticmethod
    def from_safe_encoding(encoded_uri):
        utf8 = urllib.unquote(encoded_uri)
        decoded_uri = utf8.decode('utf-8')
        return URI(decoded_uri)

    @staticmethod
    def uris_from_list(uris):
        return ([uri if isinstance(uri, URI) else URI(uri) for uri in uris]
                    if uris
                else None)

    @staticmethod
    def uris_from_safe_encoding(uris):
        return [uri if isinstance(uri, URI) else URI.from_safe_encoding(uri) for uri in uris]

    @property
    def authority(self): return self.split.netloc

    @property
    def domain(self): return URI.get_domain(self.host)
    @property

    @property
    def fragment(self): return self.split.fragment

    @property
    def host(self): return URI.get_host(self.split.netloc)

    @property
    def path(self): return self.split.path

    @property
    def path_query(self):
        return (self.split.path
                    if self.query == '' else
                self.split.path + '?' + self.query)

    @property
    def path_query_fragment(self):
        return (self.path_query
                    if self.fragment == '' else
                self.path_query + '#' + self.fragment)

    @property
    def query(self): return self.split.query

    @property
    def scheme(self): return self.split.scheme

    @property
    def dbsafe_domain(self):
#        if ' ' in self:
#            print('FOUND space in', repr(self))
        if '\r' in self.domain:
            print('FOUND cr in', repr(self.domain))
        if '\n' in self.domain:
            print('FOUND lf in', repr(self.domain))
        return URI.make_dbsafe(self.domain)

    @property
    def dbsafe_uri(self):
#        if ' ' in self:
#            print('FOUND space in', repr(self))
        if '\r' in self:
            print('FOUND cr in', repr(self))
        if '\n' in self:
            print('FOUND lf in', repr(self))
        return URI.make_dbsafe(self)

#-------------------------------------------------------------------------------

    @property
    def pathsafe_authority(self): return URI.make_pathsafe(self.authority)

    @property
    def pathsafe_base(self): return URI.make_pathsafe(self.base)

    @property
    def pathsafe_domain(self): return URI.make_pathsafe(self.domain)

    @property
    def pathsafe_host(self): return URI.make_pathsafe(self.host)

    @property
    def pathsafe_normalized_path(self):
        return URI.make_pathsafe(self.path)

    @property
    def pathsafe_normalized_path_query(self):
        return URI.make_pathsafe(self.path_query)

    @property
    def pathsafe_path_query(self): return URI.make_pathsafe(self.path_query)

    @property
    def pathsafe_path_query_fragment(self): return URI.make_pathsafe(self.path_query_fragment)

    @property
    def pathsafe_query(self): return URI.make_pathsafe(self.query)

    @property
    def pathsafe_uri(self): return URI.make_pathsafe(self)

    @property
    def websafe_uri(self):
        return URI.make_websafe(self)


#-------------------------------------------------------------------------------

    def __str__(self):
        return self.encode('utf8')

#    def __repr__(self):
#        return repr(self)

#    def __unicode__(self):
#        assert isinstance(self, unicode)
#        return self


#    def __eq__(self, other): return self == other
#    def __ne__(self, other): return self != other
#    def __gt__(self, other): return self >  other
#    def __ge__(self, other): return self >= other
#    def __lt__(self, other): return self <  other
#    def __le__(self, other): return self <= other

#    def __hash__(self):
#        s = str(self)
#        return hash(str(self))

#-------------------------------------------------------------------------------

    @staticmethod
    def decode(uri):

        def force_unicode(uri):
            '''URIs really, really need to Unicode'''
            if isinstance(uri, unicode):
                return uri
            else:
                # Try UTF-8 first because LATIN-1 works on everything
                try:
                    return unicode(uri, 'utf-8')
                except Exception:
                    return unicode(uri, 'latin-1')

        def fixup(raw_uri):
            '''Cleanup (very common) stray spaces, extra slashes, etc.'''
            raw_uri = raw_uri.strip()
            scheme, css, rest = raw_uri.partition('://')
            prefix = scheme + css
            if prefix != '':
                while rest.startswith(prefix): # drop obvious dups
                    rest = rest[len(prefix):]
            return prefix + rest.lstrip('/')

        def recursive_unquote(uri):
            '''Unquote recursively.'''
            unq = urllib.unquote(uri)
            return unq if unq == uri else recursive_unquote(unq)

        unq = recursive_unquote(uri) # Unquote first
        uni = force_unicode(unq)     # Fix embedded unicode
        unf = fixup(uni)             # Cleanup
        # Clean junk white space
        cleaned_uri = URI.clean_whitespace(unf)
        # Split so we have to the parts
        split = urlparse.urlsplit(cleaned_uri)
        fixed_netloc = split.netloc.lower()
        while '..' is fixed_netloc:
            fixed_netloc = fixed_netloc.replace('..', '.')
        normalized = urlparse.SplitResult(
                split.scheme.lower(), fixed_netloc,
                URI.normalize_path(split.path), split.query, split.fragment)
        return urlparse.urlunsplit(normalized[:4] + ('',)), normalized


    @staticmethod
    def clean_whitespace(raw_uri):
        '''Clean up whitespace.

           Remove leading and trailing whitespace.
           Remove embedded CR, LF, and TAB.'''
        partially_cleaned_uri = (raw_uri
                .replace('\r', '').replace('%0D', '').replace('%0d', '')
                .replace('\n', '').replace('%0A', '').replace('%0a', '')
                .replace('\t', '').replace('%07', '')
                .replace('%20', ' '))
        return partially_cleaned_uri.strip()


    @staticmethod
    def get_domain(host):
        if URI.IPADDR_RE.search(host) is not None:
            return 'IPADDR'
        split = host.split('.')
        if len(split) > 1 and split[0] in ['www']:
            split = split[1:]
            host = '.'.join(split)
        if len(split) <= 2:
            return host
        elif len(split[-1]) == 2 and len(split[-2]) <= 3:
            return '.'.join(split[-3:])
        else:
            return '.'.join(split[-2:])


    @staticmethod
    def get_host(authority):
        host_port = authority.split('@')[-1] if '@' in authority else authority
        return host_port.split(':')[0] if ':' in host_port else host_port


    @staticmethod
    def make_hash(raw_uri, len=5):
        '''Make a uniquifying hash for a URI.'''
        return unicode(hashlib.md5(raw_uri.encode('UTF-8')).hexdigest()[:len])

    @staticmethod
    def make_safe(uri, quote_map):
        encoded_uri = ''.join([quote_map.get(c,c) for c in uri])
        return encoded_uri

    @staticmethod
    def make_dbsafe(decoded_uri):
#        utf8 = decoded_uri.encode('utf-8')
#        pathname = urllib.quote(utf8, '!#$%&()*+,-./:;<=>?@[]^_{|}~')
#        return pathname.replace('&amp%3B', '%26')
        return decoded_uri

    pathsafe_map = dict(
        [ (unichr(c), '%' + hex(c)[2:].upper()) for c in range(0x00, 0x20) ] +
        [ (' '   , '+'  ), ('"'   , '%22'), ('%'   , '%25'), ("'"   , '%27'),
          ('/'   , '%2F'), (':'   , '%3A'), ('\\'  , '%5C'), ('`'   , '%60'),
          ('\x7F', '%7F') ])

    @staticmethod
    def make_pathsafe(decoded_uri):
        if '&amp%3B' in decoded_uri:
            print(decoded_uri)
#        return URI.make_safe(decoded_uri, '!#$%&()*+,;<=>?@[]^{|}~')
        return URI.make_safe(decoded_uri, URI.pathsafe_map)

    websafe_map = dict(
        [ (chr(c), '%' + hex(c)[2:].upper()) for c in range(0x00, 0x20) ] +
        [ (b' ', '%20'), (b'"',  '%22'),  (b'%', '%25'),
          (b"'", '%27'), (b'\\', '%5C'), (b'`', '%60') ] +
        [ (chr(c), '%' + hex(c)[2:].upper()) for c in range(0x7F, 0x100) ])

    @staticmethod
    def make_websafe(decoded_uri):
        if '&amp%3B' in decoded_uri:
            print(decoded_uri)
        utf8_uri = decoded_uri.encode('utf-8')
        return URI.make_safe(utf8_uri, URI.websafe_map)
#        return urllib.quote(utf8, '!#$&()*+,-./:;<=>?@[]^_{|}~')

    @staticmethod
    def remove_dots(uri_path):
        output = []
        for segment in uri_path.split('/'):
            if segment == '.':
                pass
            elif segment == '..':
                if len(output) > 1:
                    output.pop()
                else:
                    pass
            else:
                output.append(segment)
        return '/'.join(output)

    @staticmethod
    def normalize_path(uri_path):
        normalized_path = URI.remove_dots(uri_path)
        return normalized_path


#end
