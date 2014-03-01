#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# location.py -- File location
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

import re
import os
import sys
import hashlib
import datetime
import urllib
import pytz
import pprint
from excemptions import CreationFailed
from fingerprint_history import FingerprintHistory
from fingerprint_util import calculate_file_fingerprint
from __init__ import *

audio_ext = ['.mp3','.wav','.ogg','.wma','.flac']
audio_with_tags = ['.mp3','.ogg','.wma','.flac']
video_ext = ['.wmv','.mpeg','.mpg','.avi','.theora','.div','.divx','.flv','.mp4', 
             'm4v', '.m4a', '.mov',]

try:
    import mutagen
    from mutagen.id3 import APIC, PRIV, GEOB, MCDI, TIPL, ID3TimeStamp, UFID, TMCL, PCNT, RVA2, WCOM, COMM, Frame

except ImportError, err:
    print "mutagen isn't installed"
    print "run sudo apt-get install python-mutagen"
    exit(1)

BAD_PARTIALS = ['/resources/', '/resourcepacks/', '/assets/', '/.minecraft',
                '/minecraft']

class FileLocation:

    def __init__(self, flid=None, dirname=None, basename=None, filename=None, 
                 insert=True, *args, **kwargs):
        self.db_info = None
        self.cache_file_info = None
        if flid is not None:
            self.set_data_by_flid(flid)

        if dirname is None and basename is None and filename is None:
            raise CreationFailed(
                    "Unable to find file location information based on:\n" +
                    "   filename:%s\n" % filename + 
                    "   dirname:%s\n" % dirname +
                    "   basename:%s\n" % basename
                )
        
        if dirname and basename:
            filename = os.path.realpath(os.path.join(dirname, basename))

        if filename is not None:
            if not self.is_supported_file(filename):
                print "UNSUPPORTED:", filename
                return
            self.set_data_by_filename(filename, insert=insert)


        self.sync_db_info()
        self.sync_files_info()
        print "self.db_info:", 
        pprint.pprint(dict(self.db_info))
        print "self.file_info:", 
        pprint.pprint(dict(self.file_info))
        self.fingerprint_history = FingerprintHistory(dirname=self.dirname, 
                                                      basename=self.basename, 
                                                      flid=self.flid, 
                                                      fid=self.fid, 
                                                      fingerprint=self.fingerprint, 
                                                      front_fingerprint=self.front_fingerprint, 
                                                      middle_fingerprint=self.middle_fingerprint, 
                                                      end_fingerprint=self.end_fingerprint)

    def is_supported_file(self, filename):
        dirname, basename = os.path.split(os.path.realpath(os.path.expanduser(filename)))
        base, ext = os.path.splitext(basename)
        ext = ext.lower()
        if ext not in audio_ext and ext not in video_ext:
            return False

        for partial in BAD_PARTIALS:
            if partial in filename:
                return False
        return True

    def set_data_by_filename(self, filename, insert=True):
        dirname, basename = os.path.split(os.path.realpath(os.path.expanduser(filename)))
        print "dirname:", dirname
        print "basename:", basename
        self.db_info = get_assoc("""SELECT * 
                                    FROM file_locations 
                                    WHERE dirname = %s AND basename = %s 
                                    LIMIT 1""", 
                                (dirname, basename))
        if not self.db_info:
            if not insert:
                raise CreationFailed(
                    "Unable to find file location information based on:\n" +
                    "   filename:%s\n" % filename
                )
            self.add_file_to_db(dirname, basename)
        
        

    def set_data_by_flid(self, flid):
        self.db_info = get_assoc("""SELECT * 
                                    FROM file_locations 
                                    WHERE flid = %s 
                                    LIMIT 1""", (flid,))



    def add_file_to_db(self, dirname, basename):
        self.db_info = {}
        self.db_info['dirname'] = dirname
        self.db_info['basename'] = basename
        self.db_info = get_assoc("""INSERT INTO file_locations (dirname, basename)
                                    VALUES(%s, %s) 
                                    RETURNING *""", 
                                (dirname, basename))

    def sync_db_info(self):
        if self.changed:
            self.update_fingerprint()

    def update_fingerprint(self):
        main, front, end, middle = calculate_file_fingerprint(self.filename)
        self.db_info = get_assoc("""UPDATE file_locations 
                                    SET fingerprint = %s,
                                        front_fingerprint = %s,
                                        middle_fingerprint = %s,
                                        end_fingerprint = %s,
                                        size = %s,
                                        atime = %s,
                                        mtime = %s
                                    WHERE flid = %s
                                    RETURNING *""", 
                                (main,
                                 front,
                                 end,
                                 middle, 
                                 self.size,
                                 self.atime,
                                 self.mtime,
                                 self.flid))

    def sync_files_info(self):
        self.associate_files_info()

    def get_file_info(self):
        file_info = None
        # get_file_info_by_dirname_basename WILL BE REMOVED WHEN file_locations take over.
        # file_info = self.get_file_info_by_dirname_basename(self.dirname, self.basename)
        if not file_info:
            file_info = self.get_file_info_by_fingerprint(self.fingerprint)

        if not file_info:
            file_info = self.get_file_info_by_other_fingerprints(
                self.front_fingerprint, self.middle_fingerprint, 
                self.end_fingerprint)
        return file_info

    def associate_files_info(self):
        
        file_info = self.get_file_info()
        if file_info:
            self.file_info = file_info
            if file_info['fid'] != self.db_info['fid']:
                self.set_fid(file_info['fid'])
            self.set_file_info_fingerprints()
        else:
            self.insert_into_files()

    def set_fid(self, fid):
        self.db_info = get_assoc("""UPDATE file_locations 
                                    SET fid = %s
                                    WHERE flid = %s
                                    RETURNING * """,
                                (fid, self.flid))


    def get_file_info_by_dirname_basename(self, dirname, basename):
        return get_assoc("""SELECT *
                            FROM files 
                            WHERE dir = %s AND basename = %s
                            LIMIT 1""",
                        (dirname, basename))

    def get_file_info_by_fingerprint(self, fingerprint):
        return get_assoc("""SELECT *
                            FROM files 
                            WHERE fingerprint = %s
                            LIMIT 1""",
                        (fingerprint,))

    def get_file_info_by_other_fingerprints(self, front_fingerprint,
                                            middle_fingerprint, end_fingerprint):
        return get_assoc("""SELECT *
                            FROM files 
                            WHERE front_fingerprint = %s OR 
                                  middle_fingerprint = %s OR
                                  end_fingerprint = %s
                            LIMIT 1""",
                        (front_fingerprint, middle_fingerprint, end_fingerprint))

    def set_file_info_fingerprints(self):
        if self.fingerprints_in_sync:
            return
        query("""UPDATE files
                 SET fingerprint = %s,
                     front_fingerprint = %s,
                     middle_fingerprint = %s, 
                     end_fingerprint = %s
                WHERE fid = %s""",
             (self.fingerprint,
              self.front_fingerprint,
              self.middle_fingerprint,
              self.end_fingerprint,
              self.db_info['fid']))
        self.file_info = self.get_file_info()

    def insert_into_files(self):
        self.file_info = get_assoc("""INSERT INTO files
                                        (fingerprint, front_fingerprint,
                                         middle_fingerprint, end_fingerprint)
                                      VALUES(%s, %s, %s, %s)
                                      RETURNING *""", 
                                  (self.fingerprint,
                                   self.front_fingerprint,
                                   self.middle_fingerprint,
                                   self.end_fingerprint))

    @property
    def fingerprints_in_sync(self):
        if not self.file_info:
            return False
        keys = ['fingerprint', 'front_fingerprint', 'middle_fingerprint', 
                'end_fingerprint']
        for k in keys:
            if self.db_info[k] != self.file_info[k]:
                return False
        return True

    @property
    def changed(self):
        if (not self.db_info or 
            not self.db_info['fingerprint'] or 
            not self.db_info['front_fingerprint'] or
            not self.db_info['middle_fingerprint'] or
            not self.db_info['end_fingerprint'] or
            self.db_info['size'] != self.size or 
            self.db_info['atime'] != self.atime or 
            self.db_info['mtime'] != self.mtime):
            return True
        return False

    @property
    def size(self):
        return os.path.getsize(self.filename)

    @property
    def exists(self):
        try:
            return os.path.exists(self.filename)
        except AttributeError:
            return False
        return False

    @property
    def is_readable(self):
        if not self.exists:
            return False
        return os.access(self.filename, os.R_OK)

    @property
    def atime(self):
        return datetime.datetime.fromtimestamp(os.path.getatime(self.filename)).replace(tzinfo=pytz.UTC)

    @property
    def mtime(self):
        return datetime.datetime.fromtimestamp(os.path.getmtime(self.filename)).replace(tzinfo=pytz.UTC)

    @property
    def filename(self):
        return os.path.join(self.get_value('dirname'), self.get_value('basename'))

    @property
    def basename(self):
        return self.get_value('basename')

    @property
    def dirname(self):
        return self.get_value('dirname')

    @property
    def fid(self):
        return self.get_value('fid')

    @property
    def flid(self):
        return self.get_value('flid')

    @property
    def fingerprint(self):
        return self.get_value('fingerprint', '')

    @property
    def front_fingerprint(self):
        return self.get_value('front_fingerprint', '')

    @property
    def middle_fingerprint(self):
        return self.get_value('middle_fingerprint', '')

    @property
    def end_fingerprint(self):
        return self.get_value('end_fingerprint', '')

    @property
    def uri(self):
        filename = self.filename
        if self.exists:
            return "file://%s" % (urllib.quote(filename.encode('utf8')),)
        else:
            return urllib.quote(filename.encode('utf8'))

    def get_value(self, key, default=None):
        if not self.db_info or key not in self.db_info:
            return default
        return self.db_info[key]


if __name__ == "__main__":
    dirs = sys.argv[1:]
    for d in dirs:
        print "Dir:",d
        for root, dirs, files in os.walk(os.path.realpath(os.path.expanduser(d))):
            print "root", root
            print "dirs:", dirs
            for f in files:
                filename = os.path.join(root, f)
                if not os.access(filename, os.R_OK):
                    print "NOT READABLE:",filename
                    continue
                if ('/resources/' in filename or 
                    '/resourcepacks/' in filename or 
                    '/assets/' in filename or
                    '/.minecraft/' in filename or
                    '/minecraft' in filename):
                    print "skip:", filename
                    continue
                print "filename:", filename
                if os.path.isdir(filename):
                    print "is dir:", filename
                    continue
                base, ext = os.path.splitext(f)
                ext = ext.lower()
                if ext not in audio_ext and ext not in video_ext:
                    continue
                print "creating:", f
                FileLocation(filename=filename, insert=True)

