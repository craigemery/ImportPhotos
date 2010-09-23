#!/usr/bin/env python

#Copyright (c) 2009 Norman Craig Emery
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

dest_root = os.path.join(os.environ['USERPROFILE'], 'Documents', 'My Pictures')

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

if __name__ == "__main__":
    suffixes = ['.jpg', '.jpeg', '.mov']
    images = {}
    image_count = 0
    count = 0
    for dp, dn, fn in os.walk(sys.argv[1]):
        count += len(fn)
    print "Inspecting %s file%s" % (count, ("" if count == 1 else "s"))
    for dp, dn, fn in os.walk(sys.argv[1]):
        for f in fn:
            b, s = os.path.splitext(f)
            if s.lower() in suffixes:
                p = os.path.join(dp, f)
                gd = get_date(dp, b, s)
                if gd:
                  image_count += 1
                  (year, month, day, hour, min, sec) = gd
                  key = (year, month, day)
                  l = images.get(key, [])
                  l.append([dp, f])
                  images[key] = l

    print "Found %s image%s" % (image_count, ("" if image_count == 1 else "s"))
    keys = images.keys()
    keys.sort()
    n = 0
    for key in keys:
        (year, month, day) = key
        files = images[key]
        d = os.path.join(dest_root, year, '%s_%s_%s' % (year, month, day))
        if not os.path.isdir(d):
            print "Creating directory", d
            os.makedirs(d)
        for (dp, f) in files:
            n += 1
            dest = os.path.join(d, f)
            if not os.path.isfile(dest):
                src = os.path.join(dp, f)
                print "Copying file [%d of %d] %s to directory %s" % (n, image_count, src, d)
                shutil.copy2(src, d)
