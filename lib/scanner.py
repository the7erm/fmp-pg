#!/usr/bin/env python2
# scanner.py -- Parse files, get .mp3 info.
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
#d
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import os
from os.path import join, getsize
from lib.local_file_fobj import Local_File, CreationFailed
from file_location import FileLocation, audio_ext, video_ext, is_supported_file
from __init__ import get_assoc, query
from datetime import date
from parse_df import associate_devices

print "scanner.py called"

already_scanned = []
SKIP_DIRS = ["/.minecraft", "/resources/", "/minecraft/", '/.crazycraft/',
             "/.electriciansjourney/", "/.fellowship/", '/.technic',]

def scan_file(root=None, name=None, filename=None, hash=True):
    if filename is None:
        filename = join(root, name)
        
    if not is_supported_file(filename):
        print "skipping:", filename
        return

    if root is None:
        root, name = os.path.split(filename)
    filename = os.path.realpath(filename)

    for folder in SKIP_DIRS:
        if folder in filename:
            print "skipping:", filename
            return
    
    sql = """SELECT dirname, basename FROM file_locations 
             WHERE last_scan = current_date AND
                   dirname = %s AND
                   basename = %s"""
    already_scanned = get_assoc(sql, (root, name))
    if already_scanned:
        print "already_scanned today %s" % filename
        return

    print 'scanning:', filename
    try:
        # FileLocation(filename=filename, insert=True)
        f = Local_File(filename=filename, hash=hash, insert=True, silent=True)
        sql = """UPDATE file_locations SET last_scan = current_date 
                 WHERE dirname = %s AND basename = %s"""
        query(sql, (root, name))
    except CreationFailed:
        FileLocation(filename=filename, insert=True)
        try:
            f = Local_File(filename=filename, hash=hash, insert=True, 
                           silent=True)
            sql = """UPDATE file_locations SET last_scan = current_date 
                     WHERE dirname = %s AND basename = %s"""
            query(sql, (root, name))
        except CreationFailed:
            pass

    associate_devices()

def scan_dir(directory, hash=True):

    for folder in SKIP_DIRS:
        if folder in directory:
            print "skipping:", directory
            return

    if already_scanned.count(directory) != 0:
        return

    _files = {}
    for root, dirs, files in os.walk(directory):
        if root in already_scanned:
            continue
        already_scanned.append(root)
        skip = False
        for folder in SKIP_DIRS:
            if folder in root:
                skip = True
                break
        if skip:
            print "skipping:", root
            continue
        print "scanning:", root
        for f in files:
            filename = os.path.join(root, f)
            _files[filename] = {
                "root": root, 
                "name": f,
                "hash": hash
            }
    
    
    len_files = float(len(_files.keys()))
    i = 0
    keys = sorted(_files.keys())
    for filename in keys:
        f = _files[filename]
        print "PROGRESS: %s %.02f%% %s:%s %s %s" % (directory, (i / len_files) * 100, i, int(len_files), (i / len_files), filename)
        scan_file(**f)
        i += 1

    already_scanned.append(directory)
