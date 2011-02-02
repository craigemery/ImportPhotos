#!/usr/bin/env python

#Copyright (c) 2010,2011 Norman Craig Emery
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:
#
#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

from __future__ import with_statement

__init__ = ['Importer']

import os
import wx
from threading import Thread, Event
import re
from path_metadata import MediaMetadata
from ShellFolders import parse_dest_dirs
import time
from memory import Memory

class Importer(Thread):
    skip_dirs = ['Originals', 'Thumb', re.compile(r'^\..*')]

    def __init__(self, frame, sources, opts):
        Thread.__init__(self)
        self.started_at = time.time()
        self.interrupt = Event()
        self.frame = frame
        self.opts = opts
        self.source_dirs = []
        self.source_files = []
        for s in sources:
            if os.path.isdir(s):
                self.source_dirs.append(s)
            elif os.path.isfile(s):
                self.source_files.append(os.path.abspath(s))
        self.dest_dirs = parse_dest_dirs(opts.dest_dirs)
        self.already_imported = Memory()
        self.__msg("%sImporting media from %s" % (("" if self.dest_dirs else "Not "), ", ".join(self.source_dirs + self.source_files)))
        if self.dest_dirs:
            self.start()

    def __msg(self, s, min_verbosity = 1):
        try:
            self.__service_interrupt()
            if self.opts.verbosity >= min_verbosity:
                wx.CallAfter(self.frame.logger, s)
        except wx.PyDeadObjectError:
            self.interrupt.set()

    def __dmsg(self, s, min_verbosity = 1):
        if self.opts.dry_run:
            self.__msg("NOT %s" % (s,), min_verbosity)
        else:
            self.__msg(s, min_verbosity)

    def __twiddle(self, mode):
        self.__service_interrupt()
        if self.opts.verbosity > 1:
            wx.CallAfter(self.frame.twiddle, mode)

    def __start(self):
        self.__twiddle(0)

    def __advance(self):
        self.__twiddle(1)

    def __complete(self):
        self.__twiddle(2)

    def __service_interrupt(self):
        if self.interrupt.is_set():
          raise UserWarning("Raise Thread Quitting")

    def __find_media(self):
        from idir import idirs
        import itertools

        def desc_dirs(action, tup):
            if action == "dir":
                (dirpath, fcount, dcount) = tup
                fdets = "%d file%s" % (fcount, ("" if fcount == 1 else "s"))
                ddets = "%d sub-director%s" % (dcount, ("y" if dcount == 1 else "ies"),)
                if fcount > 0:
                    if dcount > 0:
                        para = " (%s & %s)" % (fdets, ddets)
                    else:
                        para = " (%s)" % (fdets,)
                elif dcount > 0:
                    para = " (%s)" % (ddets,)
                else:
                    para = ""
                self.__msg("Scanning directory %s%s" % (dirpath, para), 2)
            elif action == "skip":
                (skipped) = tup
                self.__msg("Skipping dir %s" % (skipped,), 2)

        ret = []
        self.__start()
        paths = idirs(self.source_dirs, desc_dirs, Importer.skip_dirs)
        if self.source_files:
            paths = itertools.chain(self.source_files, paths)
        paths = itertools.ifilter(MediaMetadata.has_media_suff, paths)
        mds = map(lambda path: MediaMetadata(path), paths)
        if self.opts.skip_already_imported and self.opts.forget is False:
            mds = itertools.ifilterfalse(lambda md: self.already_imported.known(md.digest()), mds)
        self.__complete()
        return mds

    def __examine_media(self, mds):
        # Now examine their EXIF data, if we can
        media_details = list(mds)
        media_count = len(media_details)
        ret = {}
        date_count = 0
        self.__msg("Found %s file%s (Not already inspected), now getting shot date info" % (media_count, ("" if media_count == 1 else "s")))
        self.__start()
        for md in media_details:
            self.__advance()
            dirpath = md.dirname
            base = md.basename
            suff = md.suffix
            fname = md.path
            date = md.get_date()
            if date:
                date_count += 1
                l = ret.get(date, [])
                l.append((dirpath, fname, md))
                ret[date] = l
        self.__complete()
        return (ret, date_count)

    def __runner(self):
        (media, date_count) = self.__examine_media(self.__find_media())
        self.__msg("Found shot date info of %s file%s" % (date_count, ("" if date_count == 1 else "s")))
        dates = media.keys()
        dates.sort()
        n = 0
        for date in dates:
            (year, month, day) = date
            files = media[date]
            YY = '%02d' % year
            date_dir = '%s_%02d_%02d' % (YY, month, day)

            if self.opts.forget:
                for (dirpath, fname, src_md) in files:
                    hexdigest = src_md.digest()
                    if self.already_imported.known(hexdigest):
                        self.__dmsg("Forgetting %s" % (os.path.join(dirpath, fname),))
                        if not self.opts.dry_run:
                            self.already_imported.forget(hexdigest)
                self.already_imported.commit()
            else:
                def desc_copies(action, tup):
                    (md, dest) = tup
                    kind = md.kind()
                    src = md.path
                    mention_dest = (" to %s" % (dest,)) if self.opts.verbosity > 1 else ""
                    if action == "import":
                        self.__dmsg("Importing %s [file %d of %d] %s%s" % (kind, n, date_count, src, mention_dest))
                    elif action == "already":
                        self.__msg("%s [file %d of %d] %s already imported%s" % (kind, n, date_count, src, mention_dest))
                    #elif action == "mkdir":
                        #self.__dmsg("Creating directory %s" % (dest,), 2)
                    #elif action == "!mkdir":
                        #self.__msg("Directory %s already exists" % (dest,), 2)

                for (dirpath, fname, src_md) in files:
                    n += 1
                    for dest_dir in self.dest_dirs:
                        d = os.path.join(dest_dir, YY, date_dir)
                        if src_md.copy_to(d, self.opts.dry_run, desc_copies):
                            self.already_imported.remember(src_md.digest())
        tdelta = time.time() - self.started_at
        self.__msg("All done in %.01f second%s!" % (tdelta, "" if tdelta == 1 else "s"))

    def run(self):
        from traceback import print_exc
        try:
            self.__runner()
        except Exception, e:
            print_exc()
            print "Exception %s" % (str(e),)

#vim:sw=4:ts=4
