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
from stat import ST_SIZE
import string
import shutil
import wx
from threading import Thread, Event
import EXIF
import _winreg
import platform
import ctypes

def get_free_space(folder):
    """ Return folder/drive free space (in bytes)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        s = os.statvfs(folder)
        return s.f_bfree * s.f_bsize

def user_shell_folders():
    ret = {}
    key = hive = None
    try:
        hive = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
        key = _winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        for i in range(_winreg.QueryInfoKey(key)[1]):
            name, value, val_type = _winreg.EnumValue(key, i)
            ret[name] = value
    except WindowsError:
        pass
    finally:
        if key:
            _winreg.CloseKey(key)
        if hive:
            _winreg.CloseKey(hive)
    return ret

USF = user_shell_folders()

def get_shell_dir(d):
    ret = USF.get(d, None)
    if not ret: # Not sure we need this
        ret = USF.get("My %s" % (d,), None)
    return ret

def parse_dest_dirs(l):
    ret = []
    for d in l:
        head = "<shell:"
        try:
            if d.index(head) == 0 and d[-1] == ">":
                d = get_shell_dir(d[len(head):-1])
        except:
            pass
        if d and os.path.isdir(d):
            ret.append(d)
    return ret

def get_date(dir, base, suff):
    root = os.path.join(dir, base)
    lsuff = suff.lower()
    if '.mov' == lsuff and os.path.isfile(root + ".JPG"):
        suff = '.JPG'
    path = root + suff
    ret = None
    if os.path.isfile(path):
        if '.3gp' == lsuff:
            ret = (str(2000 + int(base[0:2])), base[2:4], base[4:6], base[6:8], base[8:10], base[10:12])
        else:
            with open(path, "rb") as f:
                DTO = 'DateTimeOriginal'
                tags = EXIF.process_file(f, stop_tag=DTO)
                dto = tags.get('EXIF %s' % (DTO))
                if dto:
                    ret = string.splitfields(str(dto).replace(' ', ':'), ':')
    return ret

def file_length(fname):
    return None if not os.path.isfile(fname) else os.stat(fname)[ST_SIZE]

class Importer(Thread):
    def __init__(self, frame, source_dirs, opts):
        Thread.__init__(self)
        self.interrupt = Event()
        self.frame = frame
        self.opts = opts
        self.source_dirs = source_dirs
        self.dest_dirs = parse_dest_dirs(opts.dest_dirs)
        self.__msg("%sImporting photos from %s" % (("" if self.dest_dirs else "Not "), ", ".join(self.source_dirs)))
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

    def __progress(self, mode):
        self.__service_interrupt()
        if self.opts.verbosity > 1:
            wx.CallAfter(self.frame.twiddle, mode)

    def __service_interrupt(self):
        if self.interrupt.is_set():
          raise UserWarning("Raise Thread Quitting")

    def run(self):
        try:
            self.runner()
        except Exception, e:
            print "Exception %s" % (str(e),)

    def runner(self):
        skip_dirs = ['Originals', '.picasaoriginals']
        suffixes = ['.jpg', '.jpeg', '.mov', '.3gp']
        image_details = []
        images = {}
        # First find all the image files
        self.__progress(0)
        for source_dir in self.source_dirs:
            if os.path.isdir(source_dir):
                for dirpath, dirnames, filenames in os.walk(source_dir):
                    for fname in filenames:
                        self.__progress(1)
                        base, suff = os.path.splitext(fname)
                        if suff.lower() in suffixes:
                            image_details.append((dirpath, base, suff, fname))
                    for dir in skip_dirs:
                        for idx in range(len(dirnames)):
                            if dirnames[idx] == dir:
                                self.__progress(2)
                                self.__msg("Skipping dir %s" % (os.path.join(dirpath, dir),), 2)
                                self.__progress(0)
                                del dirnames[idx]
                                break
        self.__progress(2)
        # Now examine their EXIF data, if we can
        image_count = len(image_details)
        date_count = 0
        self.__msg("Found %s image%s, now getting shot date info" % (image_count, ("" if image_count == 1 else "s")))
        self.__progress(0)
        for dirpath, base, suff, fname in image_details:
            self.__progress(1)
            gd = get_date(dirpath, base, suff)
            if gd:
                date_count += 1
                (year, month, day, hour, min, sec) = gd
                key = (year, month, day)
                l = images.get(key, [])
                l.append([dirpath, fname])
                images[key] = l
        self.__progress(2)

        self.__msg("Found shot date info of %s image%s" % (date_count, ("" if date_count == 1 else "s")))
        keys = images.keys()
        keys.sort()
        n = 0
        for key in keys:
            (year, month, day) = key
            files = images[key]
            date_dir = '%s_%s_%s' % (year, month, day)
            for dest_dir in self.dest_dirs:
                d = os.path.join(dest_dir, year, date_dir)
                if not os.path.isdir(d):
                    self.__dmsg("Creating directory %s" % (d,), 2)
                    if not self.opts.dry_run:
                        os.makedirs(d)
                else:
                    self.__msg("Directory %s already exists" % (d,), 2)
            for (dirpath, fname) in files:
                n += 1
                for dest_dir in self.dest_dirs:
                    d = os.path.join(dest_dir, year, date_dir)
                    dest = os.path.join(d, fname)
                    src = os.path.join(dirpath, fname)
                    mention_dest = (" to %s" % (dest,)) if self.opts.verbosity > 1 else ""
                    dest_len = file_length(dest)
                    # If it's not there TO START WITH
                    if dest_len is None:
                        self.__dmsg("Importing photo [%d of %d] %s%s" % (n, date_count, src, mention_dest))
                        if not self.opts.dry_run:
                            src_len = file_length(src)
                            while src_len != dest_len:
                                # First entry to this loop, the dest is missing
                                # But when we loop, it'll be present and unequal to source
                                if dest_len is not None:
                                    # So delete the fragment
                                    os.unlink(dest)
                                # Now check there's enough free space
                                if src_len >= get_free_space(d):
                                    self.__msg("Ran out of disk space")
                                    raise Exception("Not enough free space")
                                # Attempt the copy
                                shutil.copy2(src, dest)
                                # Re-get the length
                                dest_len = file_length(dest)
                    else:
                        self.__msg("Photo [%d of %d] %s already imported%s" % (n, date_count, src, mention_dest))
        self.__msg("All done!")

#vim:sw=4:ts=4
