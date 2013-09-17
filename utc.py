# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals

'''UTC Date/time helper functions..'''
__author__ = 'Scott G. Ainsworth'
__id__ = '$Id: utc.py 512 2013-02-23 15:31:30Z sainswor $'

import calendar
from datetime import datetime
import dateutil.parser
import dateutil.tz
import time

#==================================================================
# CONSTANTS
#==================================================================

R_FORMAT   = '%Y-%m-%d %H:%M:%S'
RFC822_FORMAT   = '%a, %d %b %Y %H:%M:%S %Z'
YYYYMMDDHHMMSS_FORMAT = '%Y%m%d%H%M%S'
YYYYMMDDHHMM_FORMAT = '%Y%m%d%H%M'
YYMMDDHHMMSS_FORMAT = '%y%m%d%H%M%S'
FILESYS_FORMAT  = '%Y%m%d-%H%M%S'
_DEFAULTS_LOCAL = datetime.now(dateutil.tz.tzlocal())
_DEFAULTS_UTC   = datetime.now(dateutil.tz.tzutc())

#==================================================================
def now():
#==================================================================
    return datetime.now(dateutil.tz.tzutc())

#==================================================================
def from_parts(year, month, day, hour=0, minute=0, second=0,
               millisecond=0):
#==================================================================
    return datetime(year, month, day, hour, minute, second, millisecond,
                    dateutil.tz.tzutc())

#==================================================================
def from_timestamp(timestamp):
#==================================================================
    return datetime.fromtimestamp(timestamp, dateutil.tz.tzutc())

#==================================================================
def from_uuid(uuid):
#==================================================================
    return from_timestamp(int((uuid.time - 0x01b21dd213814000L)/1e7))

#==================================================================
def to_timestamp(dt):
#==================================================================
    return int(calendar.timegm(dt.utctimetuple()))

#==================================================================
def parse_local(dt_str):
#==================================================================
    try:
        dt = dateutil.parser.parse(dt_str, default=_DEFAULTS_LOCAL)
        if (dt.year < 120): # compensate for Y2K problems
            dt = datetime(dt.year + 1900, dt.month, dt.day, dt.hour,
                          dt.minute, dt.second, tzinfo = dt.tzinfo)
        return dt.astimezone(dateutil.tz.tzutc())
    except ValueError as ex:
        print('parse_local("{0}"): {1} ' % (dt_str, ex))
        raise

#==================================================================
def parse_utc(dt_str):
#==================================================================
    try:
        dt = dateutil.parser.parse(dt_str, default=_DEFAULTS_UTC)
        if (dt.year < 120): # compensate for Y2K problems
            dt = datetime(dt.year + 1900, dt.month, dt.day, dt.hour,
                          dt.minute, dt.second, tzinfo = dt.tzinfo)
        elif (dt.year >= 1900 and dt.year <= 1970):
            dt = datetime(dt.year + 100, dt.month, dt.day, dt.hour,
                          dt.minute, dt.second, tzinfo = dt.tzinfo)
        return dt
    except ValueError as ex:
        print('parse_utc("%s"): %s' % (dt_str, ex))
        raise

#==================================================================
def parse_rfc822(rfc822_str):
#==================================================================
    dt = datetime.strptime(rfc822_str, RFC822_FORMAT)
    return datetime(dt.year, dt.month, dt.day, dt.hour,
                    dt.minute, dt.second, 0, dateutil.tz.tzutc())

#==================================================================
def parse_yymmddhhmmss(dt_str):
#==================================================================
    dt = datetime.strptime(dt_str, YYMMDDHHMMSS_FORMAT)
    return datetime(dt.year, dt.month, dt.day, dt.hour,
                    dt.minute, dt.second, 0, dateutil.tz.tzutc())

#==================================================================
def parse_yyyymmddhhmm(dt_str):
#==================================================================
    dt = datetime.strptime(dt_str, YYYYMMDDHHMM_FORMAT)
    return datetime(dt.year, dt.month, dt.day, dt.hour,
                    dt.minute, 0, 0, dateutil.tz.tzutc())

#==================================================================
def parse_yyyymmddhhmmss(dt_str):
#==================================================================
    try:
        dt = datetime.strptime(dt_str, YYYYMMDDHHMMSS_FORMAT)
        return datetime(dt.year, dt.month, dt.day, dt.hour,
                        dt.minute, dt.second, 0, dateutil.tz.tzutc())
    except Exception as ex:
        return None

#==================================================================
def r(dt):
#==================================================================
    try:
        return dt.strftime(R_FORMAT) if dt is not None else 'N/A'
    except ValueError:
        return None

#==================================================================
def rfc822(dt):
#==================================================================
    try:
        return dt.strftime(RFC822_FORMAT)
    except ValueError:
        return None

#==================================================================
def filesys(dt):
#==================================================================
    if dt.year < 1900:
        # Ugly hack to handle years prior to 1900
        return ('{0:04}'.format(dt.year) +
                 dt.replace(1900).strftime(FILESYS_FORMAT)[4:])
    else:
        return dt.strftime(FILESYS_FORMAT)

#==================================================================
def yyyymmddhhmmss(dt):
#==================================================================
    if dt.year < 1900:
        # Ugly hack to handle years prior to 1900
        return ('{0:04}'.format(dt.year) +
                 dt.replace(1900).strftime(YYYYMMDDHHMMSS_FORMAT)[4:])
    else:
        return dt.strftime(YYYYMMDDHHMMSS_FORMAT)

#==================================================================
# __main__
#==================================================================
if __name__ == '__main__':
    print('main')
    for dt_str in [
            'Tue, 24 Jan 2012 12:12:12 UTC',
            'Tue, 24 Jan 2012 12:12:12 GMT',
            'Tue, 24-Jan-2012 12:12:12 GMT',
            'Tuesday, 24-Jan-2012 12:12:12 GMT',
            'Tue, 24 Jan 2012 12:12:12 EST',
            'Tue, 24 Jan 2012 12:12:12 -0400',
            'Tue, 24 Jan 2012 12:12:12',
            'Jan 2012 12:12:12'
            ]:
        tzdt = parse_local(dt_str)
        print('%-38s  %-30s  %s' % (dt_str, tzdt, rfc822(tzdt)))

#end

