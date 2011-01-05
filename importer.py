#!/usr/bin/env python

#Copyright (c) 2010 Norman Craig Emery
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
import string
import shutil
import wx
from threading import Thread, Event
import _winreg
import re
import pickle
from path_metadata import PathMetadata
from ShellFolders import parse_dest_dirs
import time

twelve_numbers = re.compile('^(?P<YY>\d{2})(?P<MM>\d{2})(?P<DD>\d{2})(?P<HH>\d{2})(?P<mm>\d{2})(?P<SS>\d{2})$')
# Video12141552.3gp
Video_and_numbers = re.compile('^Video(?P<MM>\d{2})(?P<DD>\d{2})(?P<HH>\d{2})(?P<mm>\d{2})$')

class Importer(Thread):
    photos = ['.jpg', '.jpeg']
    videos = ['.mov', '.3gp', '.mp4']
    skip_dirs = ['Originals', '.picasaoriginals', 'Thumb']

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
        self.already_imported = self.__reminder()
        self.__msg("%sImporting media from %s" % (("" if self.dest_dirs else "Not "), ", ".join(self.source_dirs + self.source_files)))
        if self.dest_dirs:
            self.start()

    def get_date(self, dir, base, suff):
        root = os.path.join(dir, base)
        lsuff = suff.lower()
        if '.mov' == lsuff and os.path.isfile(root + ".JPG"):
            suff = '.JPG'
        path = root + suff
        ret = None
        path_md = PathMetadata(path)
        if path_md.is_file:
            mdate = path_md.mdate()
            if lsuff in Importer.videos:
                m = twelve_numbers.search(base)
                if m:
                    ret = (2000 + int(m.group('YY')), int(m.group('MM')),  int(m.group('DD')))
                else:
                    m = Video_and_numbers.search(base)
                    if m:
                        ret = (mdate[0], int(m.group('MM')), int(m.group('DD')))
            else:
                dto = path_md.dateTimeOriginal()
                if dto:
                    (YY, MM, DD, HH, mm, ss) = string.splitfields(str(dto).replace(' ', ':'), ':')
                    ret = (int(YY), int(MM), int(DD))
            if ret is None:
                ret = mdate
        return ret

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

    def __kind(self, fname):
        base, suff = os.path.splitext(fname)
        suff = suff.lower()
        if suff in Importer.photos:
            return "photo"
        elif suff in Importer.videos:
            return "video"
        else:
            return "file (!)"

    def __reminder(self):
        self.handkerchief = os.path.join(os.path.dirname(__file__), '.already_imported')
        if os.path.isfile(self.handkerchief):
            with open(self.handkerchief, 'rb') as f:
                return pickle.load(f)
        return set()

    def __remember(self, hexdigest):
        if hexdigest not in self.already_imported:
            self.already_imported.add(hexdigest)
            with open(self.handkerchief, 'wb') as f:
                pickle.dump(self.already_imported, f)

    def __find_media(self):
        suffixes = Importer.photos + Importer.videos
        ret = []
        # First find all the media files
        self.__start()
        if self.source_files:
            self.__msg("Scanning supplied files")
        for path in self.source_files:
            dirpath, fname = os.path.split(path)
            self.__advance()
            md = PathMetadata(path)
            if self.opts.skip_already_imported:
                hexdigest = md.digest()
                if hexdigest in self.already_imported:
                    continue
            base, suff = os.path.splitext(fname)
            if suff.lower() in suffixes:
                ret.append((dirpath, base, suff, fname, md))
        if self.source_files:
            self.__msg("Done scanning supplied files")
        for source_dir in self.source_dirs:
            if os.path.isdir(source_dir):
                if PathMetadata.IS_WINDOWS and source_dir[-1] == ":":
                    source_dir += "\\"
                for dirpath, dirnames, filenames in os.walk(source_dir):
                    fcount = len(filenames)
                    dcount = len(dirnames)
                    self.__msg("Scanning directory %s (%d file%s & %d sub-director%s)" % (dirpath, fcount, ("" if fcount == 1 else "s"), dcount, ("y" if dcount == 1 else "ies"),), 2)
                    for fname in filenames:
                        self.__advance()
                        md = PathMetadata(os.path.join(dirpath, fname))
                        if self.opts.skip_already_imported:
                            hexdigest = md.digest()
                            if hexdigest in self.already_imported:
                                continue
                        base, suff = os.path.splitext(fname)
                        if suff.lower() in suffixes:
                            ret.append((dirpath, base, suff, fname, md))
                    for dir in Importer.skip_dirs:
                        for idx in range(len(dirnames)):
                            if dirnames[idx] == dir:
                                self.__msg("Skipping dir %s" % (os.path.join(dirpath, dir),), 2)
                                del dirnames[idx]
                                break
        self.__complete()
        return ret

    def __examine_media(self, media_details):
        # Now examine their EXIF data, if we can
        media_count = len(media_details)
        ret = {}
        date_count = 0
        self.__msg("Found %s file%s (Not already inspected), now getting shot date info" % (media_count, ("" if media_count == 1 else "s")))
        self.__start()
        for dirpath, base, suff, fname, md in media_details:
            self.__advance()
            date = self.get_date(dirpath, base, suff)
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
            for dest_dir in self.dest_dirs:
                d = os.path.join(dest_dir, YY, date_dir)
                if not os.path.isdir(d):
                    self.__dmsg("Creating directory %s" % (d,), 2)
                    if not self.opts.dry_run:
                        os.makedirs(d)
                else:
                    self.__msg("Directory %s already exists" % (d,), 2)
            for (dirpath, fname, md) in files:
                n += 1
                for dest_dir in self.dest_dirs:
                    d = os.path.join(dest_dir, YY, date_dir)
                    dest = os.path.join(d, fname)
                    src = os.path.join(dirpath, fname)
                    src_md = md
                    mention_dest = (" to %s" % (dest,)) if self.opts.verbosity > 1 else ""
                    dest_md = PathMetadata(dest)
                    dest_len = dest_md.size()
                    # If it's not there TO START WITH
                    kind = self.__kind(src)
                    if dest_len is None:
                        self.__dmsg("Importing %s [file %d of %d] %s%s" % (kind, n, date_count, src, mention_dest))
                        if not self.opts.dry_run:
                            src_len = src_md.size()
                            limit = 0
                            while src_len != dest_len:
                                if limit > 10: # completely arbitrary re-try limit
                                    raise UserWarning("Failed to copy %s too many times" % (src,))
                                # First entry to this loop, the dest is missing
                                # But when we loop, it'll be present and unequal to source
                                if dest_len is not None:
                                    # So delete the fragment
                                    os.unlink(dest)
                                # Now check there's enough free space
                                if src_len >= PathMetadata(d).get_free_space():
                                    raise UserWarning("Ran out of disk space")
                                # Attempt the copy
                                shutil.copy2(src, dest)
                                # Re-get the length
                                dest_len = dest_md.size(True)
                                limit += 1
                            self.__remember(src_md.digest())
                    else:
                        self.__msg("%s [file %d of %d] %s already imported%s" % (kind, n, date_count, src, mention_dest))
                        if not self.opts.dry_run:
                            self.__remember(src_md.digest())
        tdelta = time.time() - self.started_at
        self.__msg("All done in %.01f second%s!" % (tdelta, "" if tdelta == 1 else "s"))

    def run(self):
        try:
            self.__runner()
        except Exception, e:
            print "Exception %s" % (str(e),)

#vim:sw=4:ts=4
