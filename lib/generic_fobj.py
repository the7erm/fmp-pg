

from __init__ import *
import fobj
from listeners import listeners
import os


class Generic_File(fobj.FObj):
    def __init__(self, dirname=None, basename=None, filename=None, _id=None):
        
        if filename is not None:
            dirname = os.path.dirname(filename)
            basename = os.path.basename(filename)
        elif dirname is not None and basename is not None:
            filename = os.path.join(dirname, basename)

        super(Fobj, self).__init__(filename=filename, basename=basename, dirname=dirname)

        self.can_rate = False
        

    def mark_as_played(self):
        print "TODO Generic_File.mark_as_played():",self.filename
        
