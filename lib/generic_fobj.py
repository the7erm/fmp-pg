

from __init__ import *
import fobj
from listeners import listeners
import os


class Generic_File(fobj.FObj):
    def __init__(self, dirname=None, basename=None, filename=None, _id=None,
                 **kwargs):
        
        if filename is not None:
            dirname = os.path.dirname(filename)
            basename = os.path.basename(filename)
        elif dirname is not None and basename is not None:
            filename = os.path.join(dirname, basename)

        super(Fobj, self).__init__(filename=filename, basename=basename, 
                                   dirname=dirname, **kwargs)

        self.can_rate = False
        

    def mark_as_played(self,*args,**kwargs):
        print "TODO Generic_File.mark_as_played():",self.filename

    def update_history(self,*args, **kwargs):
        print "TODO: Generic_File.update_history"

    def deinc_score(self, *args, **kwargs):
        print "TODO: Generic_File.deinc_score"

