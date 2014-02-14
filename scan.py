#!/usr/bin/env python2
# scan.py -- Scan files, and add them to your database
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

from lib.__init__ import *
import os
import sys
import lib.scanner as scanner
# import lib.file_object as file_object
# file_object.pg_conn = pg_conn
# file_object.pg_cur = pg_cur
# file_object.get_results_assoc = get_results_assoc
# file_object.get_assoc = get_assoc
# file_object.query = query

args = sys.argv[1:]

# scanner.scan_dir('/home/erm/mp3/K/Keith Urban/')
usage = """
Usage:
scan.py [dir] [filename] ...

--folders             Scan all media folders in the database.
<filename>            a file to scan for media files.
<dir>                 directory to scan.

Examples:

Scan all media folders in the database.
$ scan.py --folders

Scan a directory and subdirs for media files.
$ scan.py /path/to/media/

Scan a file.
$ scan.py /path/to/file.mp3

"""
if len(args) == 0 or "--help" in args or "-h" in args or "-help" in args:
	print usage
	sys.exit()

do_hash = True

if "--no-hash" in args:
    do_hash = False

if "--folders" in args:
    folders = get_results_assoc("SELECT DISTINCT dir FROM files ORDER BY dir")
    for f in folders:
        scanner.scan_dir(f['dir'], hash=do_hash)

for arg in args:
    if arg in ("--no-hash","--folders"):
        continue
    if os.path.isdir(arg):
        scanner.scan_dir(arg, hash=do_hash)
    elif os.path.isfile(arg):
        scanner.scan_file(filename=arg, hash=do_hash)
