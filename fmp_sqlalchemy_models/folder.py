#!/usr/bin/env python
# fmp_sqlalchemy_models/folder.py -- Information about folders.
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

import os
import datetime
from baseclass import BaseClass, log
from alchemy_session import Base
from file_location import FileLocation
from constants import AUDIO_EXT, VIDEO_EXT
from sqlalchemy import Column, Integer, Unicode, DateTime, Integer, Boolean, \
                       and_
from sqlalchemy.orm.exc import NoResultFound

class Folder(BaseClass, Base):
    __tablename__ = 'folders'
    foid = Column(Integer, primary_key=True)
    dirname = Column(Unicode, index=True)
    mtime = Column(DateTime(timezone=False))
    ctime = Column(DateTime(timezone=False))
    file_count = Column(Integer, default=0)
    last_scan = Column(DateTime(timezone=True))
    scanned = Column(Boolean, default=False)
    __repr_fields__ = [
        "foid",
        'file_count',
        "dirname",
        "mtime",
        "ctime",
        "scanned"
    ]

    @property
    def needs_scan(self):
        if not self.has_media:
            return False

        mtime = self.get_mtime()
        ctime = self.get_ctime()
        file_count = self.get_files_count()
        if self.mtime != mtime:
            log.info("mtime %s != self.mtime %s", mtime, self.mtime)
        if self.ctime != ctime:
            log.info("ctime %s != self.ctime %s", ctime, self.ctime)
        if self.file_count != file_count:
            log.info("file_count %s != self.file_count %s", file_count, self.file_count)

        if not self.scanned:
            log.info("not scanned:%s", self.dirname)

        return (not self.scanned or self.mtime != mtime or self.ctime != ctime or 
                self.file_count != file_count)

    @property
    def has_media(self):
        if not hasattr(self, 'files'):
            self.get_files()

        if not self.files:
            return False

        for f in self.files:
            base, ext = os.path.splitext(f)
            ext = ext.lower()
            if ext in AUDIO_EXT or ext in VIDEO_EXT:
                return True
        return False


    def update_mtime(self):
        self.mtime = self.get_mtime()

    def update_ctime(self):
        self.mtime = self.get_ctime()

    def update_file_count(self):
        self.file_count = self.get_files_count()

    def get_mtime(self):
        self.set_stats()
        return datetime.datetime.fromtimestamp(self.file_stats.st_mtime)

    def get_ctime(self):
        self.set_stats()
        return datetime.datetime.fromtimestamp(self.file_stats.st_ctime)

    def set_stats(self, force_refresh=False):
        if force_refresh:
            self.file_stats = None

        if not hasattr(self, 'file_stats'):
            self.file_stats = None

        if self.file_stats is not None:
            return
        self.file_stats = os.stat(self.dirname)

    def update_stats(self):
        self.set_stats()
        self.mtime = self.get_mtime()
        self.ctime = self.get_ctime()
        self.file_count = self.get_files_count()

    def get_files(self):
        self.files = os.listdir(self.dirname)
        self.files.sort()
        return self.files

    def get_files_count(self):
        return len(self.get_files())

    def insert_file_into_db(self, dirname, basename, session=None):
        base, ext = os.path.splitext(basename)
        ext = ext.lower()
        if ext not in AUDIO_EXT and ext not in VIDEO_EXT:
            return
        start_time = datetime.datetime.now()
        log.info("="*80)
        # unicode(p, "utf8",errors='replace')
        # dirname = dirname.decode('utf-8', errors='replace')
        # basename = basename.decode('utf-8', errors='replace')
        location = False
        
        try:
            location = session.query(FileLocation).filter(
                and_(FileLocation.dirname==dirname,
                     FileLocation.basename==basename))\
                .limit(1)\
                .one()
            if not location.has_changed:
                log.info("Not changed:%s", location.filename)
                # location.save()
                # location.file.save()
                
                return
        except NoResultFound:
            pass

        if not location:
            location = FileLocation(dirname=dirname, basename=basename)
            log.info("scan:%s", location.filename)
            location.scan(dirname=dirname, basename=basename, save=False)
        log.info("saving:%s", location.filename)
        location.save(session=session)
        log.info("processed:%s", location)
        end_time = datetime.datetime.now()
        delta = end_time - start_time
        
        print delta.total_seconds()

    def scan(self, dirname=None, save=True, session=None):
        skip_dirs = [
            '/minecraft/',
            '/.minecraft/',
            '/resourcepacks/',
            '.local/share/Trash/',
            '/resources/',
        ]
        dirname = os.path.realpath(os.path.expanduser(dirname))
        skip = False
        for d in skip_dirs:
            if d in dirname:
                skip = True
                break
        if skip:
            log.info("Skipping:%s", dirname)
            return
        if os.path.isfile(dirname):
            dirname, basename = os.path.split(dirname)
            self.insert_file_into_db(dirname, basename, session=session)
            return
        self.dirname = dirname
        self.update_stats()
        log.info("Scanning dir:%s", dirname)
        for f in self.files:
            filename = os.path.join(dirname, f)
            if not os.path.isfile(filename):
                continue
            dirname, basename = os.path.split(filename)
            self.insert_file_into_db(dirname, basename, session=session)
        self.scanned = True
        if save:
            self.save(session=session)

    def pre_save(self, session=None):
        if self.needs_scan:
            self.scan(self.dirname, save=False, session=session)
        self.update_stats()
