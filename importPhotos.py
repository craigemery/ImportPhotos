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

import os
import string
import shutil
import wx
import threading

class Importer:
    def __init__(self, logger, source_dir, dry_run):
        self.logger = logger
        self.dry_run = dry_run
        self.source_dir = source_dir
        self.__msg("Importing photos from %s" % (self.source_dir,))

    def __user_shell_folders(self):
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

    def __get_date(self, dir, base, suff):
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

    def __get_pictures_dir(self):
        d = self.__user_shell_folders()
        ret = d.get('My Pictures', None)
        if not ret: # Not sure we need this
            ret = d.get('Pictures', None)
        return ret

    def __msg(self, s):
        wx.CallAfter(self.logger, s)

    def __dmsg(self, s):
        if self.dry_run:
            self.__msg("NOT %s" % (s,))
        else:
            self.__msg(s)

    def go(self):
        my_pictures = self.__get_pictures_dir()
        suffixes = ['.jpg', '.jpeg', '.mov']
        image_details = []
        images = {}
        # First find all the image files
        for dp, dn, fn in os.walk(self.source_dir):
            for f in fn:
                b, s = os.path.splitext(f)
                if s.lower() in suffixes:
                    image_details.append((dp, b, s, f))
        # Now examine their EXIF data, if we can
        image_count = len(image_details)
        date_count = 0
        self.__msg("Found %s image%s, now getting shot date info" % (image_count, ("" if image_count == 1 else "s")))
        for dp, b, s, f in image_details:
            gd = self.__get_date(dp, b, s)
            if gd:
                date_count += 1
                (year, month, day, hour, min, sec) = gd
                key = (year, month, day)
                l = images.get(key, [])
                l.append([dp, f])
                images[key] = l

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
            for (dp, f) in files:
                n += 1
                dest = os.path.join(d, f)
                src = os.path.join(dp, f)
                if not os.path.isfile(dest):
                    self.__dmsg("Importing photo [%d of %d] %s to %s" % (n, date_count, src, dest))
                    if not self.dry_run:
                        shutil.copy2(src, d)
                else:
                    self.__msg("Photo [%d of %d] %s already imported" % (n, date_count, src))
        self.__msg("All done!")

class MyFrame(wx.Frame):
    """ We simply derive a new class of Frame. """
    def __init__(self, parent, title, opts, source_dir):
        wx.Frame.__init__(self, parent, title=title, size=(800, 400))
        self.opts = opts
        self.source_dir = source_dir
        self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.control.SetEditable(False)
        self.Show(True)
        thr = threading.Thread(target=self.do_import)
        thr.start()

    def do_import(self):
        Importer(self.logger, self.source_dir, self.opts.dry_run).go()

    def logger(self, s):
        self.control.AppendText("%s\n" % (s,))

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--dry_run", default=False, action="store_true",
                      dest="dry_run", help="Don't do anything, do a dry run")
    (options, args) = parser.parse_args()
    if len(args) > 0:
        app = wx.App(False)
        frame = MyFrame(None, "Craig's Photo Importer", options, args[0])
        frame.Show(True)
        app.MainLoop()

# vim:sw=4:ts=4
