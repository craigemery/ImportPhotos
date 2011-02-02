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

import os
import cPickle as pickle

class Memory:
    VERSION = 2

    def __init__(self):
        self.handkerchief = os.path.join(os.path.dirname(__file__), '.already_imported')
        self.remembered = set()
        if os.path.isfile(self.handkerchief):
            with open(self.handkerchief, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, set):
                    self.remembered = data
                elif isinstance(data, list):
                    if data[0] == Memory.VERSION:
                        self.remembered = data[1]

    def remember(self, hexdigest):
        if hexdigest not in self.remembered:
            self.remembered.add(hexdigest)
            self.commit()

    def known(self, hexdigest):
        ret = hexdigest in self.remembered
        return ret

    def forget(self, hexdigest):
        self.remembered.remove(hexdigest)

    def commit(self):
        with open(self.handkerchief, 'wb') as f:
            pickle.dump([Memory.VERSION, self.remembered], f)
