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

__init__ = ['PathMetadata']

import os
import stat
import platform
import time
import EXIF
import ctypes

class PathMetadata:
    IS_WINDOWS = (platform.system() == 'Windows')
    DTO = 'DateTimeOriginal'

    def __init__(self, path):
        self.path = path
        self.is_dir = self.is_file = self.stat = self.mtime = self.exif_tags = None
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

    def read_exif(self, stop_at = None):
        if self.exif_tags is None and self.is_file:
            with open(self.path, "rb") as f:
                self.exif_tags = EXIF.process_file(f, stop_tag=stop_at)

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

    def dateTimeOriginal(self):
        self.read_exif(stop_at = PathMetadata.DTO)
        return None if self.exif_tags is None else self.exif_tags.get('EXIF %s' % (PathMetadata.DTO))

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

#vim:sw=4:ts=4
