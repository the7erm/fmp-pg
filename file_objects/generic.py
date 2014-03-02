#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# file_objects/generic.py -- Netcast file obj
#    Copyright (C) 2014 Eugene Miller <theerm@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

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

        fobj.FObj.__init__(self, filename=filename, dirname=dirname, 
                           basename=basename, **kwargs)

        self.can_rate = False
        

    def mark_as_played(self,*args,**kwargs):
        print "TODO Generic_File.mark_as_played():",self.filename

    def update_history(self,*args, **kwargs):
        print "TODO: Generic_File.update_history"

    def deinc_score(self, *args, **kwargs):
        print "TODO: Generic_File.deinc_score"

    def inc_score(self, *args, **kwargs):
        print "TODO: Generic_File.inc_score"

    def check_recently_played(self,*args, **kwargs):
        print "TODO: Generic_File.check_recently_played"

