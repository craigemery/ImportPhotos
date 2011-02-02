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

__init__ = ['PathMetadata', 'MediaMetadata']

import os
import stat
import platform
import time
import EXIF
import ctypes
import hashlib
import re
import string
import shutil

class PathMetadata(object):
    IS_WINDOWS = (platform.system() == 'Windows')
    READ_CAP_FOR_DIGEST = 1024

    def __init__(self, path):
        self.path = path
        if path is not None:
            self.exists = os.path.exists(path)
            self.dirname = os.path.dirname(path)
            self.fname = os.path.basename(path)
            self.basename, self.suffix = os.path.splitext(self.fname)
        self.date = self.hexdigest = self.is_dir = self.is_file = self.stat = self.mtime = self.exif_tags = None
        self.__isreadable()

    def __isreadable(self):
        if self.path is None:
            return
        self.is_file = os.path.isfile(self.path)
        self.is_dir = os.path.isdir(self.path)
        self.is_readable = (self.is_file or self.is_dir)

    def __stat(self, reload):
        if reload:
            if not self.is_readable:
                self.__isreadable()
            self.stat = None
        if self.is_readable and self.stat is None:
            self.stat = os.stat(self.path)

    def size(self, reload = False):
        self.__stat(reload)
        return None if self.stat is None else self.stat[stat.ST_SIZE]

    def mdate(self, reload = False):
        self.__stat(reload)
        if self.stat is not None:
            if self.mtime is None:
                self.mtime = time.localtime(self.stat[stat.ST_MTIME])
            if self.mtime is not None:
                return (self.mtime.tm_year, self.mtime.tm_mon, self.mtime.tm_mday)

    def get_free_space(self):
        """ Return folder/drive free space (in bytes)
        """
        folder = self.path
        if PathMetadata.IS_WINDOWS:
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
            return free_bytes.value
        else:
            s = os.statvfs(folder)
            return s.f_bfree * s.f_bsize

    def __read_hexdigest(self, reload = False):
        if self.is_file and (reload or self.hexdigest is None):
            m = hashlib.sha1()
            with open(self.path, 'rb') as f:
                m.update(f.read(PathMetadata.READ_CAP_FOR_DIGEST))
            self.hexdigest = m.hexdigest()

    def digest(self, reload = False):
        self.__read_hexdigest(reload)
        return self.hexdigest

    def copy_to(self, dest_dir, dry_run = False, visitor = None):
        if not os.path.isdir(dest_dir):
            visitor("mkdir", (self, dest_dir))
            if not dry_run:
                os.makedirs(dest_dir)
        else:
            visitor("!mkdir", (self, dest_dir))
        dest = os.path.join(dest_dir, self.fname)
        dest_md = PathMetadata(dest)
        dest_len = dest_md.size()
        # If it's not there TO START WITH
        kind = self.kind()
        copied = False
        if dest_len is None:
            if visitor:
                visitor("import", (self, dest))
            if not dry_run:
                src_len = self.size()
                limit = 0
                while src_len != dest_len:
                    if limit > 10: # completely arbitrary re-try limit
                        raise UserWarning("Failed to copy %s too many times" % (self.path,))
                    # First entry to this loop, the dest is missing
                    # But when we loop, it'll be present and unequal to source
                    if dest_len is not None:
                        # So delete the fragment
                        os.unlink(dest)
                    # Now check there's enough free space
                    if src_len >= PathMetadata(dest_dir).get_free_space():
                        raise UserWarning("Ran out of disk space")
                    # Attempt the copy
                    shutil.copy2(self.path, dest)
                    # Re-get the length
                    dest_len = dest_md.size(True)
                    limit += 1
                copied = True
        else:
            if visitor:
                visitor("already", (self, dest))
            if dry_run:
                copied = True
        return copied

class MediaMetadata(PathMetadata):
    DTO = 'DateTimeOriginal'
    PHOTOS = ['.jpg', '.jpeg']
    VIDEOS = ['.mov', '.3gp', '.mp4']
    SUFFIXES = PHOTOS + VIDEOS
    TWELVE_NUMBERS = re.compile('^(?P<YY>\d{2})(?P<MM>\d{2})(?P<DD>\d{2})(?P<HH>\d{2})(?P<mm>\d{2})(?P<SS>\d{2})$')
    VIDEO_AND_NUMBERS = re.compile('^Video(?P<MM>\d{2})(?P<DD>\d{2})(?P<HH>\d{2})(?P<mm>\d{2})$')

    def __init__(self, path):
        super(MediaMetadata, self).__init__(path)

    @staticmethod
    def has_media_suff(fname):
        return os.path.splitext(fname)[1].lower() in MediaMetadata.SUFFIXES

    def read_exif(self, stop_at = None):
        if self.exif_tags is None and self.is_file:
            with open(self.path, "rb") as f:
                self.exif_tags = EXIF.process_file(f, stop_tag=stop_at)

    def dateTimeOriginal(self):
        self.read_exif(stop_at = MediaMetadata.DTO)
        return None if self.exif_tags is None else self.exif_tags.get('EXIF %s' % (MediaMetadata.DTO))

    def __read_date(self, reload = False):
        if self.is_file and (reload or self.date is None):
            root = os.path.join(self.dirname, self.basename)
            suff = self.suffix
            lsuff = suff.lower()
            if '.mov' == lsuff and os.path.isfile(root + ".JPG"):
                suff = '.JPG'
            if self.is_file:
                mdate = self.mdate()
                if lsuff in MediaMetadata.VIDEOS:
                    m = MediaMetadata.TWELVE_NUMBERS.search(self.basename)
                    if m:
                        self.date = (2000 + int(m.group('YY')), int(m.group('MM')),  int(m.group('DD')))
                    else:
                        m = MediaMetadata.VIDEO_AND_NUMBERS.search(self.basename)
                        if m:
                            self.date = (mdate[0], int(m.group('MM')), int(m.group('DD')))
                else:
                    dto = self.dateTimeOriginal()
                    if dto:
                        (YY, MM, DD, HH, mm, ss) = string.splitfields(str(dto).replace(' ', ':'), ':')
                        self.date = (int(YY), int(MM), int(DD))
                if self.date is None:
                    self.date = mdate

    def get_date(self, reload = False):
        self.__read_date(reload)
        return self.date

    def kind(self):
        suff = self.suffix.lower()
        if suff in MediaMetadata.PHOTOS:
            return "photo"
        elif suff in MediaMetadata.VIDEOS:
            return "video"
        else:
            return "file (!)"

#vim:sw=4:ts=4
