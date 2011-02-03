#Copyright (c) 2011 Norman Craig Emery
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

__init__ = ['idirs']

import os
import platform

def compare(val, m):
    if isinstance(m, str):
       return m == val
    else:
       return m.match(val)

IS_WINDOWS = (platform.system() == 'Windows')

def idirs(dirs, visitor, skip_dirs):
    if dirs is None:
        dirs = []
    if skip_dirs is None:
        skip_dirs = []
    for dir in dirs:
        if os.path.isdir(dir):
            if IS_WINDOWS and dir[-1] == ":":
                dir += "\\"
            for dirpath, dirnames, filenames in os.walk(os.path.realpath(dir)):
                if visitor:
                    visitor("dir", (dirpath, len(filenames), len(dirnames)))
                for fname in filenames:
                    yield os.path.join(dirpath, fname)
                for skip in skip_dirs:
                    for idx in range(len(dirnames) -1, -1, -1):
                        if compare(dirnames[idx], skip):
                            if visitor:
                                visitor("skip", (os.path.join(dirpath, dirnames[idx])))
                            del dirnames[idx]

#vim:sw=4:ts=4
