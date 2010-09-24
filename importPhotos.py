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


import EXIF
import sys
import os
import string
import shutil

import wx

def get_date(dir, base, suff):
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

class MyFrame(wx.Frame):
    """ We simply derive a new class of Frame. """
    def __init__(self, parent, title, source_dir):
        wx.Frame.__init__(self, parent, title=title, size=(800, 400))
        self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.source_dir = source_dir
        self.msg("Importing photos from %s" % (source_dir,))
        self.control.SetEditable(False)
        self.Show(True)
        self.Bind(wx.EVT_IDLE, self.do_import)

    def msg(self, s):
        #print s
        self.control.AppendText("%s\n" % (s,))

    def do_import(self, event):
        self.Bind(wx.EVT_IDLE, None)
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
        exif_count = 0
        self.msg("Found %s image%s\nNow inspecting EXIF data" % (image_count, ("" if image_count == 1 else "s")))
        for dp, b, s, f in image_details:
            gd = get_date(dp, b, s)
            if gd:
                exif_count += 1
                (year, month, day, hour, min, sec) = gd
                key = (year, month, day)
                l = images.get(key, [])
                l.append([dp, f])
                images[key] = l

        self.msg("Found EXIF data in %s image%s" % (exif_count, ("" if exif_count == 1 else "s")))
        keys = images.keys()
        keys.sort()
        n = 0
        dest_root = os.path.join(os.environ['USERPROFILE'], 'Documents', 'My Pictures')
        for key in keys:
            (year, month, day) = key
            files = images[key]
            d = os.path.join(dest_root, year, '%s_%s_%s' % (year, month, day))
            if not os.path.isdir(d):
                self.msg("Creating directory %s" % (d,))
                os.makedirs(d)
            else:
                self.msg("Directory %s already exists" % (d,))
            for (dp, f) in files:
                n += 1
                dest = os.path.join(d, f)
                src = os.path.join(dp, f)
                if not os.path.isfile(dest):
                    self.msg("Importing photo [%d of %d] %s" % (n, exif_count, src))
                    shutil.copy2(src, d)
                else:
                    self.msg("Photo [%d of %d] %s already imported" % (n, exif_count, src))
        self.msg("All done!")

if __name__ == "__main__" and len(sys.argv) > 1:
    app = wx.App(False)
    frame = MyFrame(None, "Craig's Photo Importer", sys.argv[1])
    frame.Show(True)
    app.MainLoop()
