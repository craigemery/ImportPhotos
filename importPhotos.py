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

import wx
from importer import Importer

class MyFrame(wx.Frame):
    """ We simply derive a new class of Frame. """
    def __init__(self, parent, title, opts, source_dir):
        wx.Frame.__init__(self, parent, title=title, size=(800, 400))
        self.opts = opts
        self.source_dir = source_dir
        self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.control.SetEditable(False)
        self.Show(True)
        self.twiddle_next = 0
        self.twiddle_me = '|/-\\'
        self.twiddle_size = len(self.twiddle_me)
        self.importer = Importer(self, self.source_dir, self.opts.dry_run)

    def logger(self, s):
        self.control.AppendText("%s\n" % (s,))

    def twiddle(self, mode):
        # Mode (0, 1, 2) == (start (add first twiddle), advance, erase)
        if mode == 0:
            # append
            self.twiddle_next = 0
            self.control.AppendText(self.twiddle_me[self.twiddle_next])
        elif mode == 1:
            # replace
            lastPos = self.control.GetLastPosition()
            self.control.Replace(lastPos-1, lastPos, self.twiddle_me[self.twiddle_next])
        elif mode == 2:
            # erase
            lastPos = self.control.GetLastPosition()
            self.control.Remove(lastPos-1, lastPos)
        # Advance
        self.twiddle_next = (self.twiddle_next + 1) % self.twiddle_size

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

#vim:sw=4:ts=4
