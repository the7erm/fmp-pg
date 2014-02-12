#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fingerprint_history.py -- Fingerprint History
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
import os
import datetime
import pytz
import pprint
from fingerprint_util import calculate_file_fingerprint

class FingerprintHistory:
    def __init__(self, dirname, basename, flid=None, fid=None, fingerprint=None,
                 front_fingerprint=None, middle_fingerprint=None, end_fingerprint=None):
        self.filename = os.path.realpath(os.path.expanduser(os.path.join(dirname, basename)))
        self.dirname, self.basename = os.path.split(self.filename)
        self.flid = flid
        self.fid = fid
        self.record = None
        self.fingerprint = fingerprint
        self.front_fingerprint = front_fingerprint
        self.middle_fingerprint = middle_fingerprint
        self.end_fingerprint = end_fingerprint
        self.insert_record()
        self.history = self.get_files_for_fingerprint(self.record['fingerprint'])

    @property
    def atime(self):
        return datetime.datetime.fromtimestamp(os.path.getatime(self.filename)).replace(tzinfo=pytz.UTC)

    @property
    def mtime(self):
        return datetime.datetime.fromtimestamp(os.path.getmtime(self.filename)).replace(tzinfo=pytz.UTC)

    @property
    def size(self):
        try:
            return os.path.getsize(self.filename)
        except OSError:
            return -1

    @property
    def changed(self):
        if not self.record:
            self.get_record()
            if not self.record:
                return True

        return False

    def get_record(self):
        self.record = get_assoc("""SELECT *
                                   FROM fingerprint_history
                                   WHERE dirname = %s AND 
                                         basename = %s AND 
                                         size = %s AND 
                                         mtime = %s AND 
                                         atime = %s""",
                                (self.dirname,
                                 self.basename, 
                                 self.size, 
                                 self.mtime,
                                 self.atime))


    def insert_record(self):
        if not self.changed:
            return
        if (self.fingerprint and self.front_fingerprint and 
            self.middle_fingerprint and self.end_fingerprint):
                main = self.fingerprint
                front = self.front_fingerprint
                middle = self.middle_fingerprint
                end = self.end_fingerprint
        else:
            main, front, middle, end = calculate_file_fingerprint(self.filename)

        if self.flid is not None and self.fid is not None:
            record = get_assoc("""SELECT *
                                  FROM fingerprint_history
                                  WHERE fingerprint = %s AND
                                        front_fingerprint = %s AND
                                        middle_fingerprint = %s AND
                                        end_fingerprint = %s AND
                                        dirname = %s AND
                                        basename = %s AND
                                        flid = %s AND
                                        fid = %s""",
                                 (main,
                                  front,
                                  middle,
                                  end, 
                                  self.dirname,
                                  self.basename,
                                  self.flid,
                                  self.fid))
        elif self.flid is not None:
            record = get_assoc("""SELECT *
                                  FROM fingerprint_history
                                  WHERE fingerprint = %s AND
                                        front_fingerprint = %s AND
                                        middle_fingerprint = %s AND
                                        end_fingerprint = %s AND
                                        dirname = %s AND
                                        basename = %s AND
                                        flid = %s""",
                                 (main,
                                  front,
                                  middle,
                                  end,
                                  self.dirname,
                                  self.basename,
                                  self.flid))
        elif self.fid is not None:
            record = get_assoc("""SELECT *
                                  FROM fingerprint_history
                                  WHERE fingerprint = %s AND
                                        front_fingerprint = %s AND
                                        middle_fingerprint = %s AND
                                        end_fingerprint = %s AND
                                        dirname = %s AND
                                        basename = %s AND
                                        fid = %s""",
                                 (main,
                                  front,
                                  middle,
                                  end,
                                  self.dirname,
                                  self.basename,
                                  self.fid))
        else:
            print "ERROR fid or flid must be set"
            sys.exit()
        if record:
            self.record = get_assoc("""UPDATE fingerprint_history 
                                       SET atime = %s,
                                           mtime = %s,
                                           size = %s
                                       WHERE fphid = %s
                                       RETURNING *""",
                                   (self.atime,
                                    self.mtime,
                                    self.size,                                        
                                    record['fphid']))
            return
        if self.flid is not None and self.fid is not None:
            record = get_assoc("""INSERT INTO fingerprint_history
                                    (fingerprint, front_fingerprint, 
                                     middle_fingerprint, end_fingerprint, 
                                     dirname, basename, flid, fid,
                                     size, atime, mtime)
                                  VALUES(%s, %s, 
                                         %s, %s,
                                         %s, %s, %s, %s,
                                         %s, %s, %s)
                                  RETURNING *""",
                                 (main,
                                  front,
                                  middle,
                                  end,
                                  self.dirname,
                                  self.basename,
                                  self.flid,
                                  self.fid,
                                  self.size,
                                  self.atime,
                                  self.mtime))
        elif self.flid is not None:
            record = get_assoc("""INSERT INTO fingerprint_history
                                    (fingerprint, front_fingerprint, 
                                     middle_fingerprint, end_fingerprint,
                                     dirname, basename, flid,
                                     size, atime, mtime)
                                  VALUES(%s, %s, 
                                         %s, %s, 
                                         %s, %s, %s,
                                         %s, %s, %s)
                                  RETURNING *""",
                                 (main,
                                  front,
                                  middle,
                                  end,
                                  self.dirname,
                                  self.basename,
                                  self.flid,
                                  self.size,
                                  self.atime,
                                  self.mtime))
        elif self.fid is not None:
            record = get_assoc("""INSERT INTO fingerprint_history
                                    (fingerprint, front_fingerprint, 
                                     middle_fingerprint, end_fingerprint, 
                                     dirname, basename, fid,
                                     size, atime, mtime)
                                  VALUES(%s, %s,
                                         %s, %s,
                                         %s, %s, %s,
                                         %s, %s, %s)
                                  RETURNING *""",
                                 (main,
                                  front,
                                  middle,
                                  end,
                                  self.dirname,
                                  self.basename,
                                  self.fid,
                                  self.size,
                                  self.atime,
                                  self.mtime))
        print "INSERT:", 
        pprint.pprint(dict(record))
        if record:
            self.record = record

    def get_files_for_fingerprint(self, fingerprint):
        return get_results_assoc("""SELECT *
                                    FROM fingerprint_history
                                    WHERE fingerprint = %s""", 
                                    (fingerprint,))

if __name__ == '__main__':
    files = get_results_assoc("""SELECT * 
                                 FROM files
                                 ORDER BY dir, basename""")
    for f in files:
        spec = {
            'fid': f['fid'],
            'dirname': f['dir'],
            'basename': f['basename'],
            'fingerprint': f['fingerprint'],
            'front_fingerprint': f['front_fingerprint'],
            'middle_fingerprint': f['middle_fingerprint'],
            'end_fingerprint': f['end_fingerprint']
        }
        fph = FingerprintHistory(**spec)
        print 'fph.history', 
        pprint.pprint(fph.history)

    files = get_results_assoc("""SELECT * 
                                 FROM file_locations
                                 ORDER BY dirname, basename""")
    for f in files:
        spec = {
            'flid': f['flid'],
            'dirname': f['dirname'],
            'basename': f['basename'],
            'fingerprint': f['fingerprint'],
            'front_fingerprint': f['front_fingerprint'],
            'middle_fingerprint': f['middle_fingerprint'],
            'end_fingerprint': f['end_fingerprint']
        }
        fph = FingerprintHistory(**spec)
        print 'fph.history', 
        pprint.pprint(fph.history)
