#!/usr/bin/env python
# scanner.py -- Parse files, get .mp3 info.
#    Copyright (C) 2012 Eugene Miller <theerm@gmail.com>
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

import os
from os.path import join, getsize
import file_object

print "scanner.py called"

already_scanned = []

def scan_file(root=None, name=None, filename=None):
    if filename == None:
        filename = join(root, name)

    filename = os.path.realpath(filename)
    print 'scanning:', filename
    f = file_object.File_Obj(filename = filename, insert=True)

def scan_dir(directory):
    if already_scanned.count(directory) != 0:
        return

    for root, dirs, files in os.walk(directory):
        if already_scanned.count(root) != 0:
            continue
        already_scanned.append(root)
        for f in files:
            scan_file(root=root, name=f)
    already_scanned.append(directory)





