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
import sys
from os.path import join, getsize
from lib.local_file_fobj import Local_File, CreationFailed
from file_location import FileLocation, audio_ext, video_ext, is_supported_file
from __init__ import get_assoc, query
from datetime import date
from parse_df import associate_devices

print "scanner.py called"

already_scanned = []
SKIP_DIRS = ["/.minecraft", "/resources/", "/minecraft/", '/.crazycraft/',
             "/.electriciansjourney/", "/.fellowship/", '/.technic',
             '/CrazyCraft']

audio_ext = ['.mp3','.wav','.ogg','.wma','.flac', '.m4a']
audio_with_tags = ['.mp3','.ogg','.wma','.flac', '.m4a']
video_ext = ['.wmv','.mpeg','.mpg','.avi','.theora','.div','.divx','.flv',
             '.mp4', '.mov', '.m4v']
valid_exts = audio_ext + audio_with_tags + video_ext

def scan_file(root=None, name=None, filename=None, hash=True, dirname=None):
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
    directory = os.path.realpath(os.path.expanduser(directory))
    if not directory or not os.path.exists(directory):
        return

    print "directory:", directory
    for folder in SKIP_DIRS:
        if folder in directory:
            print "skipping:", directory
            return

    if already_scanned.count(directory) != 0:
        return

    _files = {}
    dir_files = {}
    folder_sql = """SELECT * 
                    FROM folders
                    WHERE dirname = %(dirname)s
                    LIMIT 1"""
    folder_update_sql = """UPDATE folders
                           SET mtime = %(mtime)s,
                               scan_mtime = %(scan_mtime)s
                           WHERE dirname = %(dirname)s
                           RETURNING * """
    force = "--force" in sys.argv
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
        dirname = os.path.realpath(root)
        mtime = int(os.path.getmtime(dirname))
        folder_info = get_assoc(folder_sql, {'dirname': dirname})
        try:
            folder_info = dict(folder_info)
        except:
            folder_info = {}
        
        if folder_info and folder_info.get('mtime') == mtime and \
           mtime == folder_info.get('scan_mtime') and not force:
            folder_info = dict(folder_info)
            print "SKIPPING NOTHING'S CHANGED in %s" % dirname
            continue
        print "NOT SKIPPING %s folder_info:%s mtime:%s" % (dirname, folder_info, mtime)

        dir_files[dirname] = []
        for f in files:
            base, ext = os.path.splitext(f)
            ext = ext.lower()
            if ext not in valid_exts:
                continue
            filename = os.path.join(root, f)
            dir_files[dirname].append(filename)
            _files[filename] = {
                "root": root, 
                "name": f,
                "hash": hash,
                "dirname": dirname
            }
        if not files:
            folder_info = get_assoc(folder_sql, {'dirname': dirname})
            if folder_info:
                mtime = int(os.path.getmtime(dirname))
                folder_info = dict(folder_info)
                folder_info['scan_mtime'] = mtime
                folder_info['mtime'] = mtime
                folder_info = get_assoc(folder_update_sql, folder_info)
                print "SKIPPING DIR (no files)",dict(folder_info)

    len_files = float(len(_files.keys()))
    i = 0
    keys = sorted(_files.keys())
    for filename in keys:
        f = _files[filename]
        print "PROGRESS: %s %.02f%% %s:%s %s %s" % (directory, (i / len_files) * 100, i, int(len_files), (i / len_files), filename)
        scan_file(**f)
        
        dirname = f['dirname']
        while filename in dir_files[dirname]:
            dir_files[dirname].remove(filename)
        if not dir_files[dirname] and len(dir_files[dirname]) == 0:
            folder_info = get_assoc(folder_sql, {'dirname': dirname})
            if folder_info:
                mtime = int(os.path.getmtime(dirname))
                folder_info = dict(folder_info)
                folder_info['scan_mtime'] = mtime
                folder_info['mtime'] = mtime
                folder_info = get_assoc(folder_update_sql, folder_info)
                print "UPDATED DIR",dict(folder_info)
        i += 1

    for dirname, dir_files in dir_files.items():
        if not dir_files:
            folder_info = get_assoc(folder_sql, {'dirname': dirname})
            if folder_info:
                mtime = int(os.path.getmtime(dirname))
                folder_info = dict(folder_info)
                folder_info['scan_mtime'] = mtime
                folder_info['mtime'] = mtime
                folder_info = get_assoc(folder_update_sql, folder_info)
                print "UPDATED DIR",dict(folder_info)

    already_scanned.append(directory)
