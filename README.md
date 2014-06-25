Timemap.py
==========

Python class to parse an simplify access to Memento timemaps.

There are two versions of the class:
* <code>timemap.py</code> is the original version,which was presented to the Old Dominion University Student ACM.
* <code>LinkTimemap.py</code> is my current version.  It supports the interesting "features" of real-world timemaps that I have discovered over the past few years (for example fixing up bad Memento-Datetimes).

The latest update (2014-06-24) removes the dependicies on my utc and URI classes.  Instead, only base Python and one common package (dateutil) are required.

Note that this version does not yet support RFC 7089.  I'll update this in the next few weeks.

