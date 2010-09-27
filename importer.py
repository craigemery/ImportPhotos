#!/usr/bin/env python

#Copyright (c) 2009-2010 Norman Craig Emery
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

__init__ = ['Importer']

import os
import string
import shutil
import wx
from threading import Thread

def user_shell_folders():
    import _winreg
    ret = {}
    key = hive = None
    try:
        hive = _winreg.ConnectRegistry(None, _winreg.HKEY_CURRENT_USER)
        key = _winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        for i in range(0, _winreg.QueryInfoKey(key)[1]):
            name, value, val_type = _winreg.EnumValue(key, i)
            ret[name] = value
            i += 1
    except WindowsError:
        pass
    finally:
        if key:
            _winreg.CloseKey(key)
        if hive:
            _winreg.CloseKey(hive)
    return ret

def get_pictures_dir():
    d = user_shell_folders()
    ret = d.get('My Pictures', None)
    if not ret: # Not sure we need this
        ret = d.get('Pictures', None)
    return ret

def get_date(dir, base, suff):
    import EXIF
    if '.mov' == suff.lower():
        suff = '.JPG'
    path = os.path.join(dir, base + suff)
    f = open(path, "rb")
    if f:
        DTO = 'DateTimeOriginal'
        tags = EXIF.process_file(f, stop_tag=DTO)
        dto = tags.get('EXIF %s' % (DTO))
        f.close()
        if dto:
          return string.splitfields(str(dto).replace(' ', ':'), ':')
        else:
          return None

class Importer(Thread):
    def __init__(self, frame, source_dir, dry_run):
        Thread.__init__(self)
        self.frame = frame
        self.dry_run = dry_run
        self.source_dir = source_dir
        self.pictures_dir = get_pictures_dir()
        self.__msg("Importing photos from %s" % (self.source_dir,))
        self.start()

    def __msg(self, s):
        wx.CallAfter(self.frame.logger, s)

    def __dmsg(self, s):
        if self.dry_run:
            self.__msg("NOT %s" % (s,))
        else:
            self.__msg(s)

    def __twiddle(self, mode):
        wx.CallAfter(self.frame.twiddle, mode)

    def __service_interrupt(self):
        pass

    def run(self):
        my_pictures = self.pictures_dir()
        skip_dirs = ['Originals', '.picasaoriginals']
        suffixes = ['.jpg', '.jpeg', '.mov']
        image_details = []
        images = {}
        # First find all the image files
        self.__twiddle(0)
        for dirpath, dirnames, filenames in os.walk(self.source_dir):
            for fname in filenames:
                self.__twiddle(1)
                base, suff = os.path.splitext(fname)
                if suff.lower() in suffixes:
                    image_details.append((dirpath, base, suff, fname))
            for dir in skip_dirs:
                for idx in range(len(dirnames)):
                    if dirnames[idx] == dir:
                        self.__twiddle(2)
                        self.__msg("Skipping dir %s" % (dir,))
                        self.__twiddle(0)
                        del dirnames[idx]
                        break
        self.__twiddle(2)
        # Now examine their EXIF data, if we can
        image_count = len(image_details)
        date_count = 0
        self.__msg("Found %s image%s, now getting shot date info" % (image_count, ("" if image_count == 1 else "s")))
        self.__twiddle(0)
        for dirpath, base, suff, fname in image_details:
            self.__twiddle(1)
            gd = get_date(dirpath, base, suff)
            if gd:
                date_count += 1
                (year, month, day, hour, min, sec) = gd
                key = (year, month, day)
                l = images.get(key, [])
                l.append([dirpath, fname])
                images[key] = l
        self.__twiddle(2)

        self.__msg("Found shot date info of %s image%s" % (date_count, ("" if date_count == 1 else "s")))
        keys = images.keys()
        keys.sort()
        n = 0
        for key in keys:
            (year, month, day) = key
            files = images[key]
            d = os.path.join(my_pictures, year, '%s_%s_%s' % (year, month, day))
            if not os.path.isdir(d):
                self.__dmsg("Creating directory %s" % (d,))
                if not self.dry_run:
                    os.makedirs(d)
            else:
                self.__msg("Directory %s already exists" % (d,))
            for (dirpath, fname) in files:
                n += 1
                dest = os.path.join(d, fname)
                src = os.path.join(dirpath, fname)
                if not os.path.isfile(dest):
                    self.__dmsg("Importing photo [%d of %d] %s" % (n, date_count, src))
                    if not self.dry_run:
                        shutil.copy2(src, d)
                else:
                    self.__msg("Photo [%d of %d] %s already imported" % (n, date_count, src))
        self.__msg("All done!")

#vim:sw=4:ts=4
