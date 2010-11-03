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

__init__ = ['user_shell_folders', 'get_shell_dir', 'parse_dest_dirs']

import os
import _winreg

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

_user_shell_folders = user_shell_folders()

def get_shell_dir(d):
    ret = _user_shell_folders.get(d, None)
    if not ret: # Not sure we need this
        ret = _user_shell_folders.get("My %s" % (d,), None)
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

#vim:sw=4:ts=4

